
def sidebar_permissions(request):
    user = request.user
    
    if not user.is_authenticated:
        return {}

    show_allocation = user.role == 'department_head'

    return {
        'show_subject_allocation': show_allocation,
        # Boshqa menyu ruxsatlarini ham shu yerga qo'shish mumkin
    }