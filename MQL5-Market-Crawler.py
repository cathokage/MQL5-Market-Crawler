import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
from tqdm import tqdm

# Cấu hình
DELAY_BETWEEN_REQUESTS = (1, 3)  # Thời gian delay ngẫu nhiên giữa các request (giây)
MAX_WORKERS = 5                  # Số lượng luồng tối đa
RETRY_LIMIT = 3                  # Số lần thử lại tối đa cho mỗi request

def fetch_with_retries(url, fetch_function, max_retries=RETRY_LIMIT):
    retries = 0
    while retries < max_retries:
        try:
            return fetch_function(url)
        except Exception as e:
            print(f"Error fetching {url}: {e}. Retrying {retries + 1}/{max_retries}")
            retries += 1
            time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))
    raise Exception(f"Failed to fetch {url} after {max_retries} retries")

# Hàm để lấy số lượng trang từ trang đầu tiên
def get_total_pages(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        paginator = soup.find('div', class_='market-paginator-bottom')
        if paginator:
            pages = paginator.find_all('a')
            last_page = max([int(page.get_text()) for page in pages if page.get_text().isdigit()])
            return last_page
    return 1

# Hàm để crawl một trang và trả về danh sách các sản phẩm
def crawl_page(url):
    while True:
        try:
            response = requests.get(url)
            product_list = []

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                market_top_line = soup.find('div', class_='marketTopLine')
                if market_top_line:
                    product_cards = market_top_line.find_all('div', class_='product-card')

                    for product in product_cards:
                        product_name = product.find('a', class_='product-card__title').get_text(strip=True)
                        product_link = 'https://www.mql5.com' + product.find('a', class_='product-card__title')['href']
                        product_price = product.find('a', class_='product-card__price').get_text(strip=True).replace(' USD', '').replace(' ', '')
                        product_image = product.find('img', class_='product-card__main-logo')['src']
                        product_rating = product.find('span', class_='g-rating__info').get_text(strip=True) if product.find('span', class_='g-rating__info') else 'N/A'
                        product_author = product.find('div', class_='product-card__author').get_text(strip=True) if product.find('div', class_='product-card__author') else 'N/A'
                        product_description = product.find('div', class_='product-card__description').get_text(strip=True) if product.find('div', class_='product-card__description') else 'N/A'
                        
                        product_list.append({
                            'name': product_name,
                            'link': product_link,
                            'price': float(product_price),
                            'image': product_image,
                            'rating': product_rating,
                            'author': product_author,
                            'description': product_description
                        })
                return product_list
        except Exception as e:
            print(f"Error crawling page: {e}")
        time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

# Hàm để crawl tất cả các trang
def crawl_all_pages(base_url):
    first_page_url = f"{base_url}?{filter_query}"
    total_pages = fetch_with_retries(first_page_url, get_total_pages)
    
    all_products = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for page in range(1, total_pages + 1):
            url = f"{base_url}/page{page}?{filter_query}"
            futures.append(executor.submit(fetch_with_retries, url, crawl_page))

        for future in tqdm(as_completed(futures), total=len(futures), desc="Crawling pages"):
            all_products.extend(future.result())

    return all_products

# Hỏi người dùng về các tùy chọn lọc
def get_user_input():
    print("Chọn sản phẩm muốn lọc:")
    print("1. MT4")
    print("2. MT5")
    mt_option = input("Nhập 1 hoặc 2: ")

    print("Chọn danh mục muốn lọc:")
    print("1. Expert")
    print("2. Indicator")
    print("3. Library")
    print("4. Utility")
    category_option = input("Nhập số từ 1 đến 4: ")

    price_from = None
    price_to = None
    if input("Có muốn lọc theo khoảng giá không? (Y/N): ").lower() == 'y':
        price_from = input("Nhập giá trị tối thiểu: ")
        price_to = input("Nhập giá trị tối đa: ")

    filters = []
    if input("Có muốn lọc các giá trị khác không? (Y/N): ").lower() == 'y':
        if input("Lọc theo Rating? (Y/N): ").lower() == 'y':
            filters.append("Rating=on")
        if input("Lọc theo HasReviews? (Y/N): ").lower() == 'y':
            filters.append("HasReviews=on")
        if input("Lọc theo HasRent? (Y/N): ").lower() == 'y':
            filters.append("HasRent=on")

    return mt_option, category_option, price_from, price_to, filters

# Tạo query string từ các thông số người dùng nhập
def create_filter_query(price_from, price_to, filters):
    query = []
    if price_from:
        query.append(f"PriceFrom={price_from}")
    if price_to:
        query.append(f"PriceTo={price_to}")
    query.append("count=48")
    query.extend(filters)
    return "&".join(query)

# Hỏi người dùng về các tùy chọn
mt_option, category_option, price_from, price_to, filters = get_user_input()

# Xác định base_url từ các tùy chọn
base_url = f"https://www.mql5.com/en/market/{'mt4' if mt_option == '1' else 'mt5'}/{'expert' if category_option == '1' else 'indicator' if category_option == '2' else 'library' if category_option == '3' else 'utility'}"

# Tạo query string từ các tùy chọn
filter_query = create_filter_query(price_from, price_to, filters)

# Thông báo các lựa chọn đã được áp dụng
filter_summary = f"Bắt đầu tiến hành Crawl sản phẩm thuộc {'MT4' if mt_option == '1' else 'MT5'} - danh mục {'expert' if category_option == '1' else 'indicator' if category_option == '2' else 'library' if category_option == '3' else 'utility'}"
if price_from and price_to:
    filter_summary += f" - Với giá từ {price_from} đến {price_to}"
if filters:
    filter_summary += f" - ({', '.join(filters)})"

print(filter_summary)

# Bắt đầu crawl
print("Starting to crawl all pages...")

# Crawl tất cả các trang
all_products = crawl_all_pages(base_url)

print("Finished crawling pages. Now grouping products by author...")

# Nhóm các sản phẩm theo "author"
grouped_products = {}
for product in all_products:
    author = product['author']
    if author not in grouped_products:
        grouped_products[author] = []
    grouped_products[author].append(product)

print("Finished grouping products. Now generating HTML...")

# Tạo file HTML dạng bảng
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Product List</title>
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid black;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        th, td {
            width: 20%;
        }
        .popup {
            display: none;
            position: fixed;
            z-index: 1;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgb(0,0,0);
            background-color: rgba(0,0,0,0.4);
        }
        .popup-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
        }
        .avatar {
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h2>Product List</h2>
    <label for="price-filter">Filter by Price:</label>
    <select id="price-filter" onchange="filterProducts()">
        <option value="all">All</option>
        <option value="low-to-high">Low to High</option>
        <option value="high-to-low">High to Low</option>
    </select>
    <label for="rating-filter">Filter by Rating:</label>
    <select id="rating-filter" onchange="filterProducts()">
        <option value="all">All</option>
        <option value="low-to-high">Low to High</option>
        <option value="high-to-low">High to Low</option>
    </select>
    <div id="product-list">
"""

for author, products in grouped_products.items():
    html_content += f"<h3>Author: {author}</h3>"
    html_content += """
    <table class="product-table">
        <tr>
            <th>Product Name</th>
            <th>Price (USD)</th>
            <th>Image</th>
            <th>Rating</th>
        </tr>
    """
    for i, product in enumerate(products):
        html_content += f"""
            <tr class="product-row" data-price="{product['price']}" data-rating="{product['rating']}" data-author="{author}">
                <td><a href="{product['link']}">{product['name']}</a></td>
                <td>{product['price']}</td>
                <td><img src="{product['image']}" alt="{product['name']}" class="avatar" width="50" height="50" onclick="openPopup('image-popup-{author}-{i}')"></td>
                <td>{product['rating']}</td>
            </tr>
            <div id="image-popup-{author}-{i}" class="popup" onclick="closePopup('image-popup-{author}-{i}')">
                <div class="popup-content" onclick="event.stopPropagation();">
                    <h2>{product['name']}</h2>
                    <p>{product['description']}</p>
                </div>
            </div>
        """
    html_content += "</table>"

html_content += """
    </div>
    <script>
        function openPopup(id) {
            document.getElementById(id).style.display = 'block';
        }
        function closePopup(id) {
            document.getElementById(id).style.display = 'none';
        }
        // Đóng popup khi click vào bất kỳ chỗ nào ngoài popup
        window.onclick = function(event) {
            let popups = document.getElementsByClassName('popup');
            for (let i = 0; i < popups.length; i++) {
                if (event.target == popups[i]) {
                    popups[i].style.display = 'none';
                }
            }
        }

        function filterProducts() {
            const priceFilter = document.getElementById('price-filter').value;
            const ratingFilter = document.getElementById('rating-filter').value;
            const productTables = document.querySelectorAll('.product-table');

            productTables.forEach(table => {
                const rows = Array.from(table.querySelectorAll('.product-row'));

                let sortedRows = rows;

                if (priceFilter !== 'all') {
                    sortedRows.sort((a, b) => {
                        const priceA = parseFloat(a.getAttribute('data-price'));
                        const priceB = parseFloat(b.getAttribute('data-price'));
                        return priceFilter === 'low-to-high' ? priceA - priceB : priceB - priceA;
                    });
                }

                if (ratingFilter !== 'all') {
                    sortedRows.sort((a, b) => {
                        const ratingA = parseFloat(a.getAttribute('data-rating'));
                        const ratingB = parseFloat(b.getAttribute('data-rating'));
                        return ratingFilter === 'low-to-high' ? ratingA - ratingB : ratingB - ratingA;
                    });
                }

                sortedRows.forEach(row => table.appendChild(row));
            });
        }
    </script>
</body>
</html>
"""

# Ghi nội dung HTML vào file
with open('product_list.html', 'w', encoding='utf-8') as file:
    file.write(html_content)

print("File HTML đã được tạo thành công!")
