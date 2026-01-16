document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('uploadForm');
    if (!form || !window.docTypes) return;

    const documentTypeSelect =
        document.getElementById('documentTypeSelect') ||
        form.querySelector('select[name="document_type"]');

    const fileInput = document.getElementById('id_file');
    const fileInfo = document.getElementById('fileInfo');
    const workflowPreview = document.getElementById('workflowPreview');
    const workflowSteps = document.getElementById('workflowSteps');

    function updateField(fieldId, isRequired, fieldName) {
        const field = document.getElementById(fieldId);
        if (!field) return;

        const label = document.getElementById(fieldId.replace('Field', 'Label'));
        const select = field.querySelector('select');

        if (isRequired) {
            field.style.display = 'block';
            if (label) {
                label.innerHTML = `${fieldName} <span class="text-danger">*</span>`;
            }
            if (select) {
                select.required = true;
                select.disabled = false;
            }
        } else {
            field.style.display = 'none';
            if (label) {
                label.textContent = fieldName;
            }
            if (select) {
                select.required = false;
                select.disabled = true;
                select.value = '';
            }
        }
    }

    function hideAllFields() {
        ['subjectField', 'academicYearField', 'groupField'].forEach((fieldId) => {
            const field = document.getElementById(fieldId);
            if (field) field.style.display = 'none';
        });
    }

    function updateDynamicFields() {
        if (!documentTypeSelect) return;
        const selectedValue = documentTypeSelect.value;
        if (!selectedValue) {
            hideAllFields();
            return;
        }

        const selectedId = Number.parseInt(selectedValue, 10);
        const selectedDocType = window.docTypes.find((doc) => doc.id === selectedId);
        if (!selectedDocType) {
            hideAllFields();
            return;
        }

        updateField('subjectField', selectedDocType.requires_subject, 'Fan');
        updateField('academicYearField', selectedDocType.requires_academic_year, "O'quv yili");
        updateField('groupField', selectedDocType.requires_group, 'Guruh');

        if (fileInfo) {
            const extensions = selectedDocType.allowed_extensions.join(', .');
            fileInfo.innerHTML = `<i class="bi bi-exclamation-circle"></i> Ruxsat etilgan formatlar: .${extensions}. Maksimal hajm: ${selectedDocType.max_size} MB`;
        }

        if (workflowPreview && workflowSteps) {
            if (selectedDocType.workflow && selectedDocType.workflow.trim() !== '') {
                workflowSteps.textContent = selectedDocType.workflow;
                workflowPreview.style.display = 'block';
            } else {
                workflowPreview.style.display = 'none';
            }
        }
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    }

    if (documentTypeSelect) {
        documentTypeSelect.addEventListener('change', updateDynamicFields);
        updateDynamicFields();
    }

    if (fileInput) {
        fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            const filePreview = document.getElementById('filePreview');
            const fileName = document.getElementById('fileName');
            const fileSize = document.getElementById('fileSize');

            if (file && filePreview && fileName && fileSize) {
                fileName.textContent = file.name;
                fileSize.textContent = formatFileSize(file.size);
                filePreview.style.display = 'block';
            }
        });
    }
});
