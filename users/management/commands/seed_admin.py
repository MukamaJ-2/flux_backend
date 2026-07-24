from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the initial sysadmin account: mukamajoseph010@gmail.com'

    def handle(self, *args, **kwargs):
        email = 'mukamajoseph010@gmail.com'
        password = 'Flux11.11'

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(
                f'Admin account already exists: {email}'
            ))
            return

        User.objects.create_user(
            username='mukamajoseph010',
            email=email,
            password=password,
            first_name='Joseph',
            last_name='Mukama',
            role='sysadmin',
            avatar='JM',
            must_change_password=False,
        )

        self.stdout.write(self.style.SUCCESS(
            f'✅ Sysadmin account created successfully: {email}'
        ))
