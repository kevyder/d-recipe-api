from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import RecipeSerializer

RECIPES_URL = reverse('recipe:recipe-list')

def sample_recipe(user, **params):
  defaults = {
    'title': 'Recipe',
    'time_in_minutes': 10,
    'price': 6.00
  }

  defaults.update(params)

  return Recipe.objects.create(user=user, **defaults)

class PublicRecipeApiTest(TestCase):

  def setUp(self):
    self.client = APIClient()

  def test_auth_required(self):
    response = self.client.get(RECIPES_URL)

    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeApiTest(TestCase):

  def setUp(self):
    self.client = APIClient()
    self.user = get_user_model().objects.create_user(
      'email@email.com',
      '1qazxsw2'
    )

    self.client.force_authenticate(self.user)

  def test_retrieve_recipes(self):
    sample_recipe(user=self.user)
    sample_recipe(user=self.user)

    response = self.client.get(RECIPES_URL)

    recipes = Recipe.objects.all().order_by('-id')
    serializer = RecipeSerializer(recipes, many=True)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data, serializer.data)

  def test_recipes_limited_to_user(self):
    user_two = get_user_model().objects.create_user(
      'email_two@email.com',
      '1qazxsw2'
    )

    sample_recipe(user=user_two)
    sample_recipe(user=self.user)

    response = self.client.get(RECIPES_URL)

    recipes = Recipe.objects.filter(user=self.user)
    serializer = RecipeSerializer(recipes, many=True)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data), 1)
    self.assertEqual(response.data, serializer.data)

