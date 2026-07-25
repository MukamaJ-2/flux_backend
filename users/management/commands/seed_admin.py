from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the initial sysadmin account: mukamajoseph010@gmail.com'

    def handle(self, *args, **kwargs):
        email = 'mukamajoseph010@gmail.com'
        password = 'Flux11.11'
        username = 'mukamajoseph010'

        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.filter(username=username).first()

        if user:
            user.set_password(password)
            user.role = 'sysadmin'
            user.must_change_password = False
            user.is_active = True
            user.save(update_fields=['password', 'role', 'must_change_password', 'is_active'])
            self.stdout.write(self.style.SUCCESS(
                f'Sysadmin password reset: {email}'
            ))
            return

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name='Joseph',
            last_name='Mukama',
            role='sysadmin',
            avatar='JM',
            must_change_password=False,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Sysadmin account created successfully: {email}'
        ))
