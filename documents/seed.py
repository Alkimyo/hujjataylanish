from django.contrib.auth import get_user_model
from django.db import transaction

from documents.models import Role, University, Faculty, Department, Program, Group


def seed_demo_data():
    if University.objects.exists():
        Role.initialize_default_roles()
        return

    with transaction.atomic():
        Role.initialize_default_roles()
        universities = _create_structure()
        _create_users(universities)


def _create_structure():
    universities = []
    structure = [
        {
            "university": {"name": "Namangan State University", "code": "NSU"},
            "faculties": [
                {
                    "name": "Computer Science",
                    "code": "CS",
                    "departments": [
                        {
                            "name": "Software Engineering",
                            "code": "SE",
                            "programs": [
                                {"name": "Software Engineering", "code": "SE"},
                                {"name": "Applied Software", "code": "AS"},
                            ],
                        },
                        {
                            "name": "Information Systems",
                            "code": "IS",
                            "programs": [
                                {"name": "Information Systems", "code": "IS"},
                                {"name": "Data Systems", "code": "DS"},
                            ],
                        },
                    ],
                },
                {
                    "name": "Economics",
                    "code": "EC",
                    "departments": [
                        {
                            "name": "Finance",
                            "code": "FIN",
                            "programs": [
                                {"name": "Finance", "code": "FIN"},
                                {"name": "Banking", "code": "BNK"},
                            ],
                        },
                        {
                            "name": "Accounting",
                            "code": "ACC",
                            "programs": [
                                {"name": "Accounting", "code": "ACC"},
                                {"name": "Audit", "code": "AUD"},
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "university": {"name": "Tashkent Tech University", "code": "TTU"},
            "faculties": [
                {
                    "name": "Engineering",
                    "code": "ENG",
                    "departments": [
                        {
                            "name": "Mechanical Engineering",
                            "code": "ME",
                            "programs": [
                                {"name": "Mechanical Engineering", "code": "ME"},
                                {"name": "Mechatronics", "code": "MT"},
                            ],
                        },
                        {
                            "name": "Electrical Engineering",
                            "code": "EE",
                            "programs": [
                                {"name": "Electrical Engineering", "code": "EE"},
                                {"name": "Electronics", "code": "EL"},
                            ],
                        },
                    ],
                },
                {
                    "name": "Mathematics",
                    "code": "MTH",
                    "departments": [
                        {
                            "name": "Applied Mathematics",
                            "code": "AM",
                            "programs": [
                                {"name": "Applied Mathematics", "code": "AM"},
                                {"name": "Statistics", "code": "STAT"},
                            ],
                        },
                        {
                            "name": "Computer Mathematics",
                            "code": "CM",
                            "programs": [
                                {"name": "Computer Mathematics", "code": "CM"},
                                {"name": "Data Modeling", "code": "DM"},
                            ],
                        },
                    ],
                },
            ],
        },
    ]

    for uni_data in structure:
        university, _ = University.objects.get_or_create(
            code=uni_data["university"]["code"],
            defaults={
                "name": uni_data["university"]["name"],
                "address": "Demo address",
                "website": "",
            },
        )
        universities.append(university)

        for faculty_data in uni_data["faculties"]:
            faculty, _ = Faculty.objects.get_or_create(
                university=university,
                code=faculty_data["code"],
                defaults={"name": faculty_data["name"]},
            )

            for dept_data in faculty_data["departments"]:
                department, _ = Department.objects.get_or_create(
                    faculty=faculty,
                    code=dept_data["code"],
                    defaults={"name": dept_data["name"]},
                )

                for program_data in dept_data["programs"]:
                    program, _ = Program.objects.get_or_create(
                        code=program_data["code"],
                        defaults={
                            "name": program_data["name"],
                            "department": department,
                        },
                    )

                    for year_suffix in ("22", "23"):
                        Group.objects.get_or_create(
                            program=program,
                            name=f"{program.code}-{year_suffix}",
                        )

    return universities


def _create_users(universities):
    User = get_user_model()

    def ensure_user(username, password, **kwargs):
        user, created = User.objects.get_or_create(username=username, defaults=kwargs)
        if created:
            user.set_password(password)
            user.save()
        else:
            dirty = False
            for key, value in kwargs.items():
                if getattr(user, key) != value and value is not None:
                    setattr(user, key, value)
                    dirty = True
            if dirty:
                user.save()
        return user

    teacher_role = Role.get_role_by_code("TEACHER_BASIC")
    student_role = Role.get_role_by_code("STUDENT_BASIC")
    head_role = Role.get_role_by_code("DEPARTMENT_HEAD_BASIC")
    dean_role = Role.get_role_by_code("FACULTY_DEAN_BASIC")
    director_role = Role.get_role_by_code("DIRECTOR_BASIC")

    main_university = universities[0]
    main_faculty = main_university.faculties.first()
    main_department = main_faculty.departments.first()
    main_program = main_department.programs.first()
    main_group = main_program.groups.first()

    admin = ensure_user(
        "admin",
        "admin12345",
        email="admin@example.com",
        is_superuser=True,
        is_staff=True,
    )
    if admin.active_role is None and teacher_role:
        admin.active_role = teacher_role
        admin.roles_data = teacher_role.code
        admin.save()

    dean = ensure_user(
        "dean",
        "dean12345",
        email="dean@example.com",
        university=main_university,
        faculty=main_faculty,
    )
    if teacher_role:
        dean.add_role(teacher_role)
    if dean_role:
        dean.add_role(dean_role)
    if dean.active_role is None and dean_role:
        dean.active_role = dean_role
        dean.save()
    if dean.managed_faculty is None:
        dean.managed_faculty = main_faculty
        dean.save()

    head = ensure_user(
        "dept_head",
        "head12345",
        email="head@example.com",
        university=main_university,
        faculty=main_faculty,
        department=main_department,
    )
    if teacher_role:
        head.add_role(teacher_role)
    if head_role:
        head.add_role(head_role)
    if head.active_role is None and head_role:
        head.active_role = head_role
        head.save()
    if head.managed_department is None:
        head.managed_department = main_department
        head.save()

    teacher = ensure_user(
        "teacher",
        "teacher12345",
        email="teacher@example.com",
        university=main_university,
        faculty=main_faculty,
        department=main_department,
    )
    if teacher_role:
        teacher.add_role(teacher_role)
    if teacher.active_role is None and teacher_role:
        teacher.active_role = teacher_role
        teacher.save()

    director = ensure_user(
        "director",
        "director12345",
        email="director@example.com",
        university=main_university,
    )
    if teacher_role:
        director.add_role(teacher_role)
    if director_role:
        director.add_role(director_role)
    if director.active_role is None and director_role:
        director.active_role = director_role
        director.save()

    student1 = ensure_user(
        "student1",
        "student12345",
        email="student1@example.com",
        university=main_university,
        faculty=main_faculty,
        department=main_department,
        program=main_program,
        group=main_group,
    )
    if student_role:
        student1.add_role(student_role)
    if student1.active_role is None and student_role:
        student1.active_role = student_role
        student1.save()

    student2 = ensure_user(
        "student2",
        "student12345",
        email="student2@example.com",
        university=main_university,
        faculty=main_faculty,
        department=main_department,
        program=main_program,
        group=main_group,
    )
    if student_role:
        student2.add_role(student_role)
    if student2.active_role is None and student_role:
        student2.active_role = student_role
        student2.save()
