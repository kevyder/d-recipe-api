import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse("recipe:recipe-list")


def image_upload_url(recipe_id):
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


def detail_url(recipe_id):
    return reverse("recipe:recipe-detail", args=[recipe_id])


def sample_tag(user, name="Tag One"):
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name="Tomato"):
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    defaults = {"title": "Recipe", "time_in_minutes": 10, "price": 6.00}

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
        self.user = get_user_model().objects.create_user("email@email.com", "1qazxsw2")

        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipes_limited_to_user(self):
        user_two = get_user_model().objects.create_user(
            "email_two@email.com", "1qazxsw2"
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
        payload = {"title": "Bread", "time_in_minutes": 30, "price": 1.00}

        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data["id"])

        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        tag_one = sample_tag(user=self.user, name="Vegan")
        tag_two = sample_tag(user=self.user, name="Dessert")

        payload = {
            "title": "Pizza",
            "tags": [tag_one.id, tag_two.id],
            "time_in_minutes": 60,
            "price": 14.06,
        }

        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data["id"])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag_one, tags)
        self.assertIn(tag_two, tags)

    def test_create_recipe_with_ingredients(self):
        ingredient_one = sample_ingredient(user=self.user, name="Tomato")
        ingredient_two = sample_ingredient(user=self.user, name="Onion")

        payload = {
            "title": "Pasta",
            "ingredients": [ingredient_one.id, ingredient_two.id],
            "time_in_minutes": 60,
            "price": 14.06,
        }

        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data["id"])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient_one, ingredients)
        self.assertIn(ingredient_two, ingredients)

    def test_partial_update_recipe(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user)

        payload = {"title": "Sancocho", "tags": [new_tag.id]}

        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        payload = {"title": "Lemonade", "time_in_minutes": 25, "price": 23.00}

        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.time_in_minutes, payload["time_in_minutes"])
        self.assertEqual(recipe.price, payload["price"])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)


class RecipeImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("email@email.com", "1qazxsw2")

        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            response = self.client.post(url, {"image": ntf}, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("image", response.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        response = self.client.post(url, {"image": "notimage"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        recipe_one = sample_recipe(user=self.user, title="Curry")
        recipe_two = sample_recipe(user=self.user, title="Tahini")

        tag_one = sample_tag(user=self.user, name="Vegan")
        tag_two = sample_tag(user=self.user, name="Vegetarian")

        recipe_one.tags.add(tag_one)
        recipe_two.tags.add(tag_two)

        recipe_three = sample_recipe(user=self.user, title="Ajiaco")

        response = self.client.get(RECIPES_URL, {"tags": f"{tag_one.id},{tag_two.id}"})
        serializer_one = RecipeSerializer(recipe_one)
        serializer_two = RecipeSerializer(recipe_two)
        serializer_three = RecipeSerializer(recipe_three)

        self.assertIn(serializer_one.data, response.data)
        self.assertIn(serializer_two.data, response.data)
        # self.assertNotIn(serializer_three.data, response.data)

    def test_filter_recipes_by_ingredients(self):
        recipe_one = sample_recipe(user=self.user, title="Cubios")
        recipe_two = sample_recipe(user=self.user, title="Sopa du Macaco")

        ingredient_one = sample_ingredient(user=self.user, name="Water")
        ingredient_two = sample_ingredient(user=self.user, name="Macaco Monkey")

        recipe_one.ingredients.add(ingredient_one)
        recipe_two.ingredients.add(ingredient_two)

        recipe_three = sample_recipe(user=self.user, title="Chunchullo")

        response = self.client.get(
            RECIPES_URL, {"ingredients": f"{ingredient_one.id}, {ingredient_two.id}"}
        )

        serializer_one = RecipeSerializer(recipe_one)
        serializer_two = RecipeSerializer(recipe_two)
        serializer_three = RecipeSerializer(recipe_three)

        self.assertIn(serializer_one.data, response.data)
        self.assertIn(serializer_two.data, response.data)
        # self.assertNotIn(serializer_three.data, response.data)
