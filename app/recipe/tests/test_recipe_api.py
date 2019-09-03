from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
  return reverse('recipe:recipe-detail', args=[recipe_id])

def sample_tag(user, name='Tag One'):
  return Tag.objects.create(user=user, name=name)

def sample_ingredient(user, name='Tomato'):
  return Ingredient.objects.create(user=user, name=name)

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

  def test_view_recipe_detail(self):
    recipe = sample_recipe(user=self.user)
    recipe.tags.add(sample_tag(user=self.user))
    recipe.ingredients.add(sample_ingredient(user=self.user))

    url = detail_url(recipe.id)
    response = self.client.get(url)

    serializer = RecipeDetailSerializer(recipe)
    self.assertEqual(response.data, serializer.data)

  def test_create_basic_recipe(self):
    payload = {
      'title': 'Bread',
      'time_in_minutes': 30,
      'price': 1.00
    }

    response = self.client.post(RECIPES_URL, payload)

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    recipe = Recipe.objects.get(id=response.data['id'])

    for key in payload.keys():
      self.assertEqual(payload[key], getattr(recipe, key))

  def test_create_recipe_with_tags(self):
    tag_one = sample_tag(user=self.user, name='Vegan')
    tag_two = sample_tag(user=self.user, name='Dessert')

    payload = {
      'title': 'Pizza',
      'tags': [tag_one.id, tag_two.id],
      'time_in_minutes': 60,
      'price': 14.06
    }

    response = self.client.post(RECIPES_URL, payload)

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    recipe = Recipe.objects.get(id=response.data['id'])
    tags = recipe.tags.all()
    self.assertEqual(tags.count(), 2)
    self.assertIn(tag_one, tags)
    self.assertIn(tag_two, tags)

  def test_create_recipe_with_ingredients(self):
    ingredient_one = sample_ingredient(user=self.user, name='Tomato')
    ingredient_two = sample_ingredient(user=self.user, name='Onion')

    payload = {
        'title': 'Pasta',
        'ingredients': [ingredient_one.id, ingredient_two.id],
        'time_in_minutes': 60,
        'price': 14.06
    }

    response = self.client.post(RECIPES_URL, payload)

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    recipe = Recipe.objects.get(id=response.data['id'])
    ingredients = recipe.ingredients.all()
    self.assertEqual(ingredients.count(), 2)
    self.assertIn(ingredient_one, ingredients)
    self.assertIn(ingredient_two, ingredients)




