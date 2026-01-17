"""
QR Code Generation and PDF Integration Service
"""

import qrcode
import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import black

class QRCodeService:
    
    QR_SIZE_MM = 40  
    
    @classmethod
    def generate_qr_code_image(cls, document):
        verification_url = cls._get_verification_url(document)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=1,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        return qr.make_image(fill_color="black", back_color="white")
    
    @classmethod
    def save_qr_image(cls, document):
        """QR kodni modelga saqlash"""
        qr_image = cls.generate_qr_code_image(document)
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"qr_{document.uuid}.png"
        document.qr_code_image.save(filename, ContentFile(buffer.read()), save=True)
        return document.qr_code_image

    @classmethod
    def generate_final_pdf(cls, document):
        """Asl PDF oxiriga yangi tasdiqlash sahifasini qo'shish"""
       
        if document.status != 'approved':
            raise ValueError("Hujjat tasdiqlanmagan")
        
        if not document.qr_code_image:
            cls.save_qr_image(document)
        
        original_pdf_path = document.file.path
        
        if not os.path.exists(original_pdf_path):
            raise FileNotFoundError(f"Fayl topilmadi: {original_pdf_path}")
        
        # Chiqish fayli yo'li
        output_filename = f"approved_{document.uuid}.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, 'approved_documents', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # PDF o'quvchi va yozuvchi
        reader = PdfReader(original_pdf_path)
        writer = PdfWriter()
        
        # 1. Asl hujjatning barcha sahifalarini qo'shamiz
        for page in reader.pages:
            writer.add_page(page)
            
        # 2. Yangi alohida sahifa yaratamiz (Verification Page)
        verification_page_buffer = cls._create_verification_page(document)
        verification_reader = PdfReader(verification_page_buffer)
        
        writer.add_page(verification_reader.pages[0])
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        document.final_pdf.name = f'approved_documents/{output_filename}'
        document.save(update_fields=['final_pdf'])
    
    @classmethod
    def _create_verification_page(cls, document):
        """
        Yangi A4 sahifa yaratish:
        - O'ng burchak: QR kod
        - Chap burchak: Rasmiy matn
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        width, height = A4
        margin = 20 * mm
        qr_size = cls.QR_SIZE_MM * mm
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - margin, "ELEKTRON HUJJAT TASDIQLASH VARAQASI")
        
        c.setLineWidth(1)
        c.line(margin, height - margin - 5*mm, width - margin, height - margin - 5*mm)
        
        content_top_y = height - margin - 20*mm
        
        qr_x = width - margin - qr_size
        qr_y = content_top_y - qr_size
        
        if document.qr_code_image:
            qr_path = document.qr_code_image.path
            c.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size)
            
        c.setFont("Helvetica", 8)
        c.drawCentredString(qr_x + (qr_size/2), qr_y - 4*mm, "Skaner qiling")

        text_x = margin
        text_y = content_top_y

        max_text_width = qr_x - margin - 10*mm
        
        c.setFillColor(black)
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(text_x, text_y, f"Hujjat ID: {document.verification_code}")
        
        if document.completed_at:
            date_str = document.completed_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawString(text_x, text_y - 15, f"Tasdiqlangan sana: {date_str}")
        
        c.drawString(text_x, text_y - 30, f"Hujjat turi: {document.document_type.name}")
        c.drawString(text_x, text_y - 45, f"UUID: {document.uuid}")
        #c.drawString(text_x, text_y - 45, f"Yuklovchi: {document.uploaded_by.get_full_name()}")

        # Qonuniy matn
        c.setFont("Helvetica", 9)
        text_start_y = text_y - 70
        
        legal_text = (
            "Mazkur hujjat O'zbekiston Respublikasi Vazirlar Mahkamasining 2017-yil 15-sentabrdagi 728-son "
            "qaroriga muvofiq DocFlow tizimida shakllantirilgan elektron hujjatning nusxasi hisoblanadi. "
            "Davlat organlari tomonidan ushbu hujjatni qabul qilishni rad etish qat'iyan taqiqlanadi."
        )
        
        verify_text = (
            f"Hujjatning haqiqiyligini {cls._get_site_domain()} veb-saytida hujjatning "
            "noyob raqamini kiritib yoki o'ng tomondagi QR-kodni mobil telefon yordamida "
            "skaner qilish orqali tekshirish mumkin."
        )

        # Matnni chizish funksiyasi (wrapped)
        text_obj = c.beginText(text_x, text_start_y)
        text_obj.setFont("Helvetica", 9)
        text_obj.setLeading(12) # Qatorlar orasi
        
        def add_wrapped_paragraph(canvas_obj, txt_obj, text, max_w):
            words = text.split()
            line = []
            for word in words:
                test_line = ' '.join(line + [word])
                w = canvas_obj.stringWidth(test_line, "Helvetica", 9)
                if w < max_w:
                    line.append(word)
                else:
                    txt_obj.textLine(' '.join(line))
                    line = [word]
            if line:
                txt_obj.textLine(' '.join(line))
                
        add_wrapped_paragraph(c, text_obj, legal_text, max_text_width)
        text_obj.textLine("") # Bo'sh qator
        add_wrapped_paragraph(c, text_obj, verify_text, max_text_width)
        
        c.drawText(text_obj)
        
        # Sahifani tugatish
        c.showPage()
        c.save()
        
        buffer.seek(0)
        return buffer
    
    @classmethod
    def verify_document(cls, verification_input, qr_data=None):
        from .models import Document
        document = None
        
        if verification_input:
            verification_input = verification_input.strip().upper()
            try:
                document = Document.objects.get(verification_code=verification_input, status='approved')
            except Document.DoesNotExist:
                pass
        
        if not document and qr_data:
            uuid_str = cls._extract_uuid_from_url(qr_data)
            if uuid_str:
                try:
                    document = Document.objects.get(uuid=uuid_str, status='approved')
                except Document.DoesNotExist:
                    pass
        
        if document:
            return {
                'verified': True,
                'document': document,
                'file_url': document.final_pdf.url if document.final_pdf else document.file.url,
                'uploaded_by': document.uploaded_by.get_full_name(),
                'approved_at': document.completed_at,
                'document_type': document.document_type.name,
            }
        else:
            return {'verified': False, 'error': 'Hujjat topilmadi.'}
    
    @staticmethod
    def _get_verification_url(document):
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        return f"{base_url}/verify/{document.uuid}/"
    
    @staticmethod
    def _get_site_domain():
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        return base_url.replace('http://', '').replace('https://', '').split('/')[0]

    @staticmethod
    def _extract_uuid_from_url(url):
        import re
        pattern = r'/verify/([a-f0-9-]{36})'
        match = re.search(pattern, url)
        return match.group(1) if match else None
