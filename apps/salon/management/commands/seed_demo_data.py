from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.salon.models import Aidata, Appointment, MasterSchedule, Service, Status, Transaction
from apps.users.models import AccessRight, Role, User


class Command(BaseCommand):
    help = "Create demo data for the hair salon backend."

    def handle(self, *args, **options):
        client_role, _ = Role.objects.get_or_create(
            role_name="Client",
            defaults={"role_description": "Salon client"},
        )
        master_role, _ = Role.objects.get_or_create(
            role_name="Master",
            defaults={"role_description": "Salon master"},
        )
        admin_role, _ = Role.objects.get_or_create(
            role_name="Admin",
            defaults={"role_description": "Salon administrator"},
        )

        rights = [
            (admin_role, "manage", "all", "full"),
            (master_role, "read", "appointments", "own"),
            (client_role, "read", "appointments", "own"),
        ]
        for role, operation_name, access_object, permission in rights:
            AccessRight.objects.get_or_create(
                role=role,
                operation_name=operation_name,
                access_object=access_object,
                permission=permission,
            )

        admin_user, _ = User.objects.get_or_create(
            username="admin_demo",
            defaults={
                "full_name": "Demo Admin",
                "email": "admin_demo@example.com",
                "role": admin_role,
            },
        )
        admin_user.role = admin_role
        admin_user.set_password("AdminPass123!")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        client_user, _ = User.objects.get_or_create(
            username="client_demo",
            defaults={
                "full_name": "Demo Client",
                "email": "client_demo@example.com",
                "role": client_role,
            },
        )
        client_user.role = client_role
        client_user.set_password("ClientPass123!")
        client_user.save()

        master_user, _ = User.objects.get_or_create(
            username="master_demo",
            defaults={
                "full_name": "Demo Master",
                "email": "master_demo@example.com",
                "role": master_role,
            },
        )
        master_user.role = master_role
        master_user.set_password("MasterPass123!")
        master_user.save()

        statuses = [
            ("pending", "Pending", "booking", "yellow"),
            ("confirmed", "Confirmed", "booking", "green"),
            ("completed", "Completed", "booking", "blue"),
            ("cancelled", "Cancelled", "booking", "red"),
        ]
        created_statuses = {}
        for code, name, group, color in statuses:
            status_obj, _ = Status.objects.get_or_create(
                status_code=code,
                defaults={
                    "status_name": name,
                    "status_group": group,
                    "color_indicator": color,
                },
            )
            created_statuses[code] = status_obj

        service, _ = Service.objects.get_or_create(
            service_name="Men haircut",
            defaults={
                "duration_minutes": 60,
                "price": Decimal("1200.00"),
                "category": "Haircut",
            },
        )

        MasterSchedule.objects.get_or_create(
            master=master_user,
            day_of_week=1,
            start_time="10:00",
            end_time="18:00",
            defaults={"is_workday": True, "breaks": "13:00-14:00"},
        )

        appointment, _ = Appointment.objects.get_or_create(
            client=client_user,
            master=master_user,
            service=service,
            start_datetime=timezone.now() + timedelta(days=1),
            defaults={
                "status": created_statuses["pending"],
                "comment": "Demo appointment",
                "payment_status": Appointment.PaymentStatus.UNPAID,
            },
        )

        transaction, _ = Transaction.objects.get_or_create(
            appointment=appointment,
            external_id="DEMO-PAYMENT-001",
            defaults={
                "amount": service.price,
                "payment_method": "cash",
                "status": "paid",
            },
        )

        Aidata.objects.update_or_create(
            appointment=appointment,
            defaults={
                "input_features": {
                    "previous_visits": 3,
                    "late_cancellations": 0,
                    "no_shows": 0,
                    "days_until_appointment": 1,
                    "prepaid": True,
                    "loyalty_score": 5,
                },
                "target_value": 0,
                "prediction_probability": Decimal("5.00"),
                "model_version": "seed-v1",
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data created or refreshed successfully."))
        self.stdout.write("Admin: admin_demo / AdminPass123!")
        self.stdout.write("Master: master_demo / MasterPass123!")
        self.stdout.write("Client: client_demo / ClientPass123!")
