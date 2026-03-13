#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Парсер цен Wildberries для GitHub Codespaces (использует системный ChromeDriver).
Читает артикулы из articles.xlsx, сохраняет результат в Excel.
Многопоточность, headless-режим.
"""

import os
import time
import random
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ======================== НАСТРОЙКИ ========================
INPUT_FILE = "articles.xlsx"               # файл с артикулами (колонка "Артикул")
OUTPUT_FILE = f"prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
MAX_WORKERS = 5                            # количество потоков
HEADLESS = True                             # True для сервера
PAGE_LOAD_TIMEOUT = 20                       # таймаут загрузки страницы
# ============================================================

def create_driver():
    """Создаёт headless Chrome (драйвер должен быть в PATH)."""
    chrome_options = Options()
    
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
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

def process_article(article):
    """Обрабатывает один артикул."""
    url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    print(f"    [Арт. {article}] Загружаю...")
    
    driver = create_driver()
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
        
        print(f"    [Арт. {article}] ✅ Цена: {price}, Название: {name[:30] if name else 'None'}...")
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
    finally:
        driver.quit()

def main():
    print("🚀 Запуск парсера (используется системный ChromeDriver)")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Файл {INPUT_FILE} не найден. Создай его с колонкой 'Артикул'.")
        return
    
    df_in = pd.read_excel(INPUT_FILE)
    if 'Артикул' not in df_in.columns:
        print("❌ В файле нет колонки 'Артикул'.")
        return
    
    articles = df_in['Артикул'].tolist()
    print(f"📥 Загружено {len(articles)} артикулов.")
    
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_article = {executor.submit(process_article, art): art for art in articles}
        for future in as_completed(future_to_article):
            result = future.result()
            if result:
                results.append(result)
    
    df_out = pd.DataFrame(results)
    df_out.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Готово! Сохранено {len(results)} записей в файл {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
