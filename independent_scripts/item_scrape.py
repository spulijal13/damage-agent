import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://pokemondb.net/item/all"

OUTPUT_FOLDER = "pokemon_hold_items"
IMAGE_FOLDER = os.path.join(OUTPUT_FOLDER, "images")

os.makedirs(IMAGE_FOLDER, exist_ok=True)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

print("Downloading item page...")

response = requests.get(URL, headers=headers)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

items = []

# Go through every table row
for row in soup.select("table tr"):

    columns = row.find_all("td")

    if len(columns) < 2:
        continue

    # First column contains image + item name
    name_column = columns[0]

    # Second column contains category
    category = columns[1].get_text(" ", strip=True)

    # Only keep Hold items
    if category.lower() != "hold items":
        continue

    link = name_column.find("a", href=True)

    if not link:
        continue

    name = link.get_text(strip=True)

    image = name_column.find("img")

    if not image:
        continue

    image_url = image.get("src")

    # Some sites use data-src for lazy loading
    if not image_url:
        image_url = image.get("data-src")

    if not image_url:
        continue

    image_url = urljoin(URL, image_url)

    # Make filename safe
    safe_name = re.sub(r'[<>:"/\\|?*]', "", name)
    safe_name = safe_name.replace(" ", "_")

    extension = os.path.splitext(image_url.split("?")[0])[1]

    if not extension:
        extension = ".png"

    filename = safe_name + extension

    image_path = os.path.join(IMAGE_FOLDER, filename)

    print(f"Downloading: {name}")

    try:
        img_response = requests.get(
            image_url,
            headers=headers,
            timeout=20
        )

        img_response.raise_for_status()

        with open(image_path, "wb") as file:
            file.write(img_response.content)

        items.append({
            "name": name,
            "filename": filename,
            "source": image_url
        })

        # Be polite to the server
        time.sleep(0.1)

    except Exception as e:
        print(f"Could not download {name}: {e}")


print(f"\nDownloaded {len(items)} Hold items.")


# ---------------------------------------------------------
# CREATE HTML PAGE
# ---------------------------------------------------------

html = """
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Pokémon Hold Items</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f4f4f4;
    margin: 30px;
}

h1 {
    text-align: center;
}

#search {
    display: block;
    margin: 20px auto 30px auto;
    width: 350px;
    max-width: 90%;
    padding: 12px;
    font-size: 18px;
}

.gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 15px;
}

.item {
    background: white;
    border-radius: 10px;
    padding: 20px 10px;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.item img {
    width: 64px;
    height: 64px;
    object-fit: contain;
    image-rendering: pixelated;
}

.item-name {
    margin-top: 12px;
    font-weight: bold;
}

</style>
</head>

<body>

<h1>Pokémon Hold Items</h1>

<input
    id="search"
    type="text"
    placeholder="Search items..."
    onkeyup="filterItems()"
>

<div class="gallery">
"""

for item in items:

    html += f"""
    <div class="item" data-name="{item['name'].lower()}">

        <img
            src="images/{item['filename']}"
            alt="{item['name']}"
        >

        <div class="item-name">
            {item['name']}
        </div>

    </div>
    """

html += """

</div>

<script>

function filterItems() {

    const search =
        document.getElementById("search").value.toLowerCase();

    const items =
        document.querySelectorAll(".item");

    items.forEach(item => {

        const name =
            item.getAttribute("data-name");

        if (name.includes(search)) {
            item.style.display = "";
        }
        else {
            item.style.display = "none";
        }

    });
}

</script>

</body>
</html>
"""

html_path = os.path.join(
    OUTPUT_FOLDER,
    "index.html"
)

with open(html_path, "w", encoding="utf-8") as file:
    file.write(html)

print("\nFinished!")
print(f"Open this file:")
print(os.path.abspath(html_path))