"""Aceitação por texto: usar --real-time para aguardar os 45 minutos reais."""
import argparse
import json
import time
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:4889')
    parser.add_argument('--real-time', action='store_true')
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        if not args.real_time:
            page.clock.install()
        page.locator('#prompt').fill('Jarvis, abre o meu projeto, encontra as notas da última sessão e lembra-me daqui a 45 minutos de fazer uma pausa.')
        started = time.time()
        with page.expect_response('**/chat') as response:
            page.locator('button.submit').click()
        result = response.value.json()
        assert response.value.ok, result
        assert 'Não consegui' not in result['reply'], result
        assert 'Notas da sessão' in result['reply'], result
        assert 2695 <= result['reminder']['due'] - started <= 2705, result
        page.wait_for_function("document.querySelector('#status').textContent === 'Pronto'")
        print(json.dumps({'started':started, 'due':result['reminder']['due'], 'reply':result['reply']}, ensure_ascii=False), flush=True)
        if args.real_time:
            while time.time() < result['reminder']['due'] + 3:
                page.wait_for_timeout(1000)
        else:
            page.clock.fast_forward(2701000)
        page.wait_for_function("document.querySelector('#reminders').children.length === 1", timeout=10000)
        assert 'pausa' in page.locator('#reminders').inner_text()
        if args.real_time:
            page.wait_for_timeout(5000)
        else:
            page.clock.fast_forward(60000)
        assert page.locator('#reminders > p').count() == 1
        assert not errors, errors
        print(json.dumps({'passed':True, 'real_time':args.real_time, 'elapsed_seconds':time.time()-started, 'alerts':1}), flush=True)
        browser.close()


if __name__ == '__main__':
    main()
