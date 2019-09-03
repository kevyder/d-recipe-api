from django.test import TestCase
from django.contrib.auth import get_user_model

from unittest.mock import patch

from core import models

def sample_user(email='email@email.com', password='1qazxsw2'):
  return get_user_model().objects.create_user(email, password)

class ModelTests(TestCase):

  def test_create_user_with_email_successfull(self):
    email = 'email@email.com'
    password = '1qazxsw2'
    user = get_user_model().objects.create_user(
      email = email,
      password = password
    )

    self.assertEqual(user.email, email)
    self.assertTrue(user.check_password(password))

  def test_new_user_email_normalized(self):
    email = 'test@EMAIL.com'
    user = get_user_model().objects.create_user(email, 'test123')

    self.assertEqual(user.email, email.lower())

  def test_new_user_invalid_email(self):
    with self.assertRaises(ValueError):
      get_user_model().objects.create_user(None, 'test123')

  def test_create_new_superuser(self):
    user = get_user_model().objects.create_superuser(
      'email@email.com',
      '1qazxsw2'
    )

    self.assertTrue(user.is_superuser)
    self.assertTrue(user.is_staff)

  def test_tag_str(self):
    tag = models.Tag.objects.create(
      user = sample_user(),
      name = 'Vegan'
    )

    self.assertEqual(str(tag), tag.name)

  def test_ingredient_str(self):
    ingredient = models.Ingredient.objects.create(
      user = sample_user(),
      name = 'Cucumber'
    )

    self.assertEqual(str(ingredient), ingredient.name)

  def test_recipe_str(self):
    recipe = models.Recipe.objects.create(
      user = sample_user(),
      title = 'Steak',
      time_in_minutes = 5,
      price = 5.00
    )

  @patch('uuid.uuid4')
  def test_recipe_file_name_uuid(self, mock_uuid):
    uuid = 'test-uuid'
    mock_uuid.return_value = uuid
    file_path = models.recipe_image_file_path(None, 'myimage.jpg')

    exp_path = f'uploads/recipe/{uuid}.jpg'
    self.assertEqual(file_path, exp_path)

