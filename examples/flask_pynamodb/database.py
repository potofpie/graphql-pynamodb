from uuid import uuid4


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from models import Department, Employee, SalaryEmployee, HourlyEmployee,  Role
    for model in [Department, Employee, Role]:
        if model.exists():
            model.delete_table()
        model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)

    # Create the fixtures
    engineering = Department(id=str(uuid4()), name='Engineering')
    engineering.save()
    hr = Department(id=str(uuid4()), name='Human Resources')
    hr.save()

    manager = Role(id=str(uuid4()), name='manager')
    manager.save()

    engineer = Role(id=str(uuid4()), name='engineer')
    engineer.save()

    peter = SalaryEmployee(id=str(uuid4()), name='Peter', department=engineering, role=engineer, health=True, salary=100)
    peter.save()

    roy = SalaryEmployee(id=str(uuid4()), name='Roy', department=engineering, role=engineer, health=True, salary=100)
    roy.save()

    tracy = HourlyEmployee(id=str(uuid4()), name='Tracy', department=hr, role=manager, hourly=1)
    tracy.save()
