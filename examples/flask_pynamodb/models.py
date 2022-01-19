from datetime import datetime

from graphene_pynamodb.relationships import OneToOne
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, BooleanAttribute, DiscriminatorAttribute
from pynamodb.models import Model


class Department(Model):
    class Meta:
        table_name = 'flask_pynamodb_example_department'
        host = "http://localhost:8000"

    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()


class Role(Model):
    class Meta:
        table_name = 'flask_pynamodb_example_roles'
        host = "http://localhost:8000"

    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()


class Employee(Model):
    class Meta:
        table_name = 'flask_pynamodb_example_employee'
        host = "http://localhost:8000"

    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    hired_on = UTCDateTimeAttribute(default=datetime.now)
    department = OneToOne(Department)
    role = OneToOne(Role)
    cls = DiscriminatorAttribute()

class SalaryEmployee(Employee, discriminator='SalaryEmployee'):
    class Meta:
        table_name = 'flask_pynamodb_example_employee'
        host = "http://localhost:8000"
    salary = NumberAttribute()
    health = BooleanAttribute()


class HourlyEmployee(Employee, discriminator='HourlyEmployee'):
    class Meta:
        table_name = 'flask_pynamodb_example_employee'
        host = "http://localhost:8000"
    hourly = NumberAttribute()

