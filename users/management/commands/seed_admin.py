from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the initial sysadmin account: mukamajoseph010@gmail.com'

    def handle(self, *args, **kwargs):
        email = 'mukamajoseph010@gmail.com'
        password = 'lux11.11'
        username = 'mukamajoseph010'

        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.filter(username=username).first()

        if user:
            # Ensure the account is a sysadmin and active, but do NOT
            # reset the password — the user may have changed it.
            changed = False
            if user.role != 'sysadmin':
                user.role = 'sysadmin'
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                user.save(update_fields=['role', 'is_active'])
                self.stdout.write(self.style.SUCCESS(
                    f'Sysadmin account updated (role/active): {email}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Sysadmin account already exists: {email}'
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
