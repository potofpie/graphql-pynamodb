import graphene
from graphene import relay
from graphene_pynamodb import PynamoConnectionField, PynamoObjectType
from models import Department as DepartmentModel
from models import Employee as EmployeeModel
from models import SalaryEmployee as SalaryEmployeeModel
from models import HourlyEmployee as HourlyEmployeeModel


from models import Role as RoleModel


class Department(PynamoObjectType):

    class Meta:
        model = DepartmentModel
        interfaces = (relay.Node,)




class HourlyEmployee(PynamoObjectType):
    class Meta:
        model = HourlyEmployeeModel
        interfaces = (relay.Node,)

class SalaryEmployee(PynamoObjectType):
    class Meta:
        model = SalaryEmployeeModel
        interfaces = (relay.Node,)

class Employee(PynamoObjectType):
    class Meta:
        model = EmployeeModel
        interfaces = (relay.Node,)

class Role(PynamoObjectType):
    class Meta:
        model = RoleModel
        interfaces = (relay.Node,)




class Query(graphene.ObjectType):
    node = relay.Node.Field()

    all_hourly_employees = PynamoConnectionField(HourlyEmployee)
    all_salary_employees = PynamoConnectionField(SalaryEmployee)
    all_employees = PynamoConnectionField(Employee)



    all_roles = PynamoConnectionField(Role)
    role = graphene.Field(Role)



schema = graphene.Schema(query=Query, types=[Department, Employee, Role])
