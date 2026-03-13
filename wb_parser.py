#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Парсер цен Wildberries для GitHub Codespaces.
Последовательная обработка, один драйвер на все артикулы.
Использует webdriver-manager и расширенные настройки Chrome.
"""

import os
import time
import random
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManager

# ======================== НАСТРОЙКИ ========================
INPUT_FILE = "articles.xlsx"
OUTPUT_FILE = f"prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
PAGE_LOAD_TIMEOUT = 20
HEADLESS = True  # Можно отключить для отладки (поставить False)
# ============================================================

def create_driver():
    """Создаёт драйвер с headless Chrome и дополнительными флагами."""
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--window-size=1920,1080")  # Задаём размер окна
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Иногда помогает
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Автоматическая установка драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def extract_price(driver):
    """Извлекает цену."""
    selectors = [
        "ins.price-block__final-price",
        "span.final-price",
        "span.price-block__price",
        "[class*='price-block__final-price']",
        "[data-link*='price']",
        ".product-page__price-block .price-block__final-price",
    ]
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            text = element.text.strip()
            cleaned = text.replace('₽', '').replace(' ', '').replace(',', '.').replace('\u2009', '')
            if cleaned and cleaned.replace('.', '').isdigit():
                return float(cleaned)
        except NoSuchElementException:
            continue
    try:
        meta_price = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='price']")
        content = meta_price.get_attribute("content")
        if content:
            return float(content)
    except:
        pass
    return None

def extract_name(driver):
    """Извлекает название."""
    selectors = [
        "h1.product-page__title",
        ".product-page__title",
        "[data-link*='product-page__title']",
        "h1"
    ]
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except NoSuchElementException:
            continue
    return None

def extract_brand(driver):
    """Извлекает бренд."""
    selectors = [
        "a.product-page__header-brand",
        ".product-page__brand",
        ".brand-name",
        "a[href*='?brand=']"
    ]
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except NoSuchElementException:
            continue
    return None

def process_article(driver, article):
    """Обрабатывает один артикул с уже созданным драйвером."""
    url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    print(f"    [Арт. {article}] Загружаю...")
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ins.price-block__final-price, span.final-price, .product-page__title"))
            )
        except TimeoutException:
            print(f"    [Арт. {article}] ❌ Таймаут")
            return None
        time.sleep(random.uniform(2, 4))
        price = extract_price(driver)
        name = extract_name(driver)
        brand = extract_brand(driver)
        print(f"    [Арт. {article}] ✅ Цена: {price}")
        return {
            'Артикул': article,
            'Название': name,
            'Бренд': brand,
            'Цена': price,
            'Дата': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"    [Арт. {article}] ❌ Ошибка: {e}")
        return None

def main():
    print("🚀 Запуск парсера (последовательная обработка, один драйвер)")
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Файл {INPUT_FILE} не найден.")
        return
    df_in = pd.read_excel(INPUT_FILE)
    if 'Артикул' not in df_in.columns:
        print("❌ В файле нет колонки 'Артикул'.")
        return
    articles = df_in['Артикул'].tolist()
    print(f"📥 Загружено {len(articles)} артикулов.")
    driver = create_driver()
    results = []
    try:
        for idx, art in enumerate(articles, 1):
            print(f"\n📦 Обрабатываю {idx}/{len(articles)}: артикул {art}")
            result = process_article(driver, art)
            if result:
                results.append(result)
            if idx < len(articles):
                sleep_time = random.uniform(15, 25)  # задержка между запросами
                print(f"💤 Ожидание {sleep_time:.1f} сек...")
                time.sleep(sleep_time)
    finally:
        driver.quit()
    df_out = pd.DataFrame(results)
    df_out.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Готово! Файл сохранён: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()