import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@cornerconsole.com")
    full_name = factory.Faker("name")
    phone_number = factory.LazyAttribute(lambda _: "+919876543210")
    address = factory.Faker("address")
    is_active = True
    is_verified = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "testpass123!"
        self.set_password(password)
        if create:
            self.save()
