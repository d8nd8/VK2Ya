import json
import requests
from tqdm.auto import tqdm
from pprint import pprint

class VKAPIClient:
    API_BASE_URL = "https://api.vk.com/method"

    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id

    def get_common_params(self):
        return {
            "access_token": self.token,
            "v": "5.199",
            "extended": 1,
            "photo_sizes": 1
        }

    def get_photos(self):
        params = self.get_common_params()
        params.update({"owner_id": self.user_id, "album_id": "wall"})
        response = requests.get(f"{self.API_BASE_URL}/photos.get", params=params)
        response.raise_for_status()
        result = response.json()
        return result

    @staticmethod
    def largest_photo_url(photo):
        max_size = max(photo["sizes"], key=lambda size: size["height"] * size["width"])
        return max_size["url"], max_size["type"]

class YandexAPIClient:
    API_BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"

    def __init__(self, token):
        self.token = token

    def create_folder(self, folder_name):
        headers = {
            "Authorization": f"OAuth {self.token}"
        }
        params = {
            "path": folder_name,
        }
        response = requests.put(self.API_BASE_URL, headers=headers, params=params)
        if response.status_code == 201:
            print(f"Папка '{folder_name}' успешно создана на Яндекс.Диске.")
        elif response.status_code == 409:
            print(f"Папка '{folder_name}' уже существует на Яндекс.Диске.")
        else:
            print(f"Ошибка при создании папки на Яндекс.Диске. Код ошибки: {response.status_code}")

    def upload_photo(self, url, folder_name, filename):
        upload_url = f"{self.API_BASE_URL}/upload"
        headers = {
            "Authorization": f"OAuth {self.token}"
        }
        params = {
            "path": f"{folder_name}/{filename}",
            "url": url
        }
        try:
            response = requests.post(upload_url, headers=headers, params=params)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Не удалось загрузить фотографию {filename}: {e}")
            return False

    def save_photos_info(self, photo_data, json_file):
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(photo_data, f)
        print(f"Информация о фотографиях сохранена в файл '{json_file}'.")


if __name__ == "__main__":
    vk_token = input("Введите ваш VK токен: ")
    ya_token = input("Введите ваш OAuth токен Яндекс: ")
    user_id = input("Введите ID пользователя VK: ")
    folder_name = input("Введите название папки на Яндекс.Диске: ")

    num_photos = input("Введите количество фотографий для сохранения (по умолчанию 5, нажмите Enter для продолжения): ")
    if not num_photos.strip() == "":
        num_photos = int(num_photos)
    else:
        num_photos = 5

    vk_client = VKAPIClient(vk_token, user_id)
    ya_client = YandexAPIClient(ya_token)

    try:
        photos_info = vk_client.get_photos().get("response", {}).get("items", [])
        if not photos_info:
            raise ValueError("Не удалось получить фотографии")
    except Exception as e:
        print(f"Ошибка при получении фотографий: {e}")
        exit(1)

    try:
        ya_client.create_folder(folder_name)
    except Exception as e:
        print(f"Не удалось создать папку на Яндекс.Диске: {e}")
        exit(1)

    photo_max_sizes = []
    for photo in photos_info:
        max_size = max(photo["sizes"], key=lambda size: size["height"] * size["width"])
        photo_max_sizes.append((photo, max_size["height"] * max_size["width"]))

    photo_max_sizes.sort(key=lambda x: x[1], reverse=True)
    top_photos = [photo[0] for photo in photo_max_sizes[:num_photos]]

    photo_data = []
    with tqdm(total=num_photos, desc="Загрузка фотографий на Яндекс.Диск", position=0, leave=True, colour="green") as pbar_total:
        for idx, photo in enumerate(top_photos, start=1):
            likes = photo['likes']['count']
            filename = f"{likes}.jpg"

            largest_photo_url, largest_photo_size = VKAPIClient.largest_photo_url(photo)
            success = ya_client.upload_photo(largest_photo_url, folder_name, filename)

            if success:
                pbar_total.update(1)
                print(f"\nФотография '{filename}' успешно загружена на Яндекс.Диск. ({idx}/{num_photos})")

            photo_info = {
                "file_name": filename,
                "size": largest_photo_size
            }
            photo_data.append(photo_info)

    json_file = "photos_info.json"
    ya_client.save_photos_info(photo_data, json_file)

    with open(json_file, "r") as f:
        photos_info_json = json.load(f)
        pprint(photos_info_json)
