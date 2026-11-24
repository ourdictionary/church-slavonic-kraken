# Модель kraken для церковнославянской печати

Распознаёт книги, набранные синодальным церковнославянским шрифтом, — от изданий конца XIX века до современных. Читает буквы вместе с ударениями, придыханиями и титлами.

Модель сделана проектом «Словесица» ([slovesitsa.org](https://slovesitsa.org)). Ею прочитаны Пролог (1895–1897), Минея общая новомученикам (2012), церковнославянская часть Следованной Псалтири (1993) и другие книги.

Файл модели — `cu_synodal_v1.safetensors` (64 МБ). Проверена в [kraken](https://kraken.re) 7.1.1 (нужен Python 3.10–3.13). Лицензия — Apache 2.0.

## Как распознать страницу

```
pip install kraken==7.1.1
kraken -i page.png page.txt segment -bl ocr -m cu_synodal_v1.safetensors
```

В `page.txt` будет текст страницы по строкам. Чтобы получить ещё и положение строк (PAGE XML):

```
kraken -x -i page.png page.xml segment -bl ocr -m cu_synodal_v1.safetensors
```

- Разворот сначала разрежьте на две страницы.
- В Google Colab после установки выполните ещё `pip uninstall -y transformers`: с этим пакетом kraken 7.1.1 не запускается.
- Модель пишет текст в разложенном Юникоде (NFD): ударения и титла идут отдельными знаками после буквы. Набор church-slavonic-ocr записан в составном (NFC), в нём «ᲂу» вместо «оу» и «_» вместо дефиса. Чтобы сравнивать с ним, переведите выход: `python3 to_andreev.py page.txt > page_cu.txt`. Прочитанное от этого не меняется, а без перевода ошибок насчитается в несколько раз больше.

## Точность

Доля неверных знаков (CER) с учётом ударений, придыханий и титл.

| Что читали | Строк | CER |
|---|---|---|
| Готовые вырезки строк из набора [church-slavonic-ocr](https://github.com/slavonic/church-slavonic-ocr) А. Андреева, 7 книг | 269 | 1,09 % |

Набор — версия 16ba0a9 с 48 исправлениями эталона, которые мы ему отправили. Ошибки считали функциями из его программы `cu_eval.py`, после `to_andreev.py`; без перевода выходит 4,98 %. Его модель для Tesseract на тех же строках ошибается в 5,69 % знаков. Сами эти строки в обучение не входили, но другие строки с тех же страниц входили, поэтому на незнакомой книге ошибок будет больше.

По книгам: Октоих (М., 2021) — 0,52 %, Триодь цветная (М., 2002) — 0,92 %, Минея дополнительная (М., 2018) — 0,93 %, Праздники нотного пения (СПб., 1900) — 1,43 %, Требник (Белград, 2008) — 1,88 %, службы новомученикам (Джорданвилль, 1983) и Ксении Петербургской (Джорданвилль, без года) — 0,74 и 0,85 % (6 и 15 строк).

## Ограничения

- Плохие сканы модель читает заметно хуже. На сканах Пролога в 1 бит она путала «т» с «г», «в» с «б» и теряла ударения над словами под титлом.
- На некоторых книгах модель теряет надстрочные знаки: на репринте ноябрьской Минеи (1994) треть многосложных слов вышла без ударения.
- Красную печать модель читает хуже чёрной, а цвет не различает.
- Гражданскую печать, греческий, старопечатные (дониконовские) книги и рукописи мы не проверяли.

## Как дообучить под свою книгу

Нужны строки этой книги с верным текстом: картинка строки `x.png` и рядом текст `x.gt.txt`. Нескольких сотен строк уже хватает: после 534 строк Минеи дополнительной (2018) наша предыдущая модель стала ошибаться на 62 проверочных строках с тех же страниц в 1,5 % знаков вместо 3,4 % (строки с запасом, как ниже).

- Над строкой и под ней нужен запас, чтобы ударения и титла не обрезались: высота картинки — примерно в 3,5 раза больше высоты строчной буквы. Строки второго шага обучения мы дополняли до такой высоты полем цвета фона.
- Проверочные строки берите с отдельных страниц. Если они вперемешку с обучающими, проверка покажет слишком хороший результат.

```
ketos compile -f path -o train.arrow train/*.png
ketos compile -f path -o val.arrow val/*.png
echo val.arrow > val.txt
ketos -d cuda:0 train -f binary -i cu_synodal_v1.safetensors --resize union -u NFD -N 8 -q fixed -r 0.0001 --augment -B 4 -o my_model -e val.txt train.arrow
```

`-d cuda:0` — обучение на видеокарте; в Colab подойдёт T4. На 2 319 строках 8 эпох заняли около 85 минут. Лучшая модель — файл `best_….safetensors` в папке `my_model`.

## Откуда модель

Основа — многоязычная модель PP-OCRv6 medium для kraken (Бенжамен Кисслинг, [Zenodo](https://doi.org/10.5281/zenodo.21788410), Apache 2.0). Устройство сети взято из PP-OCRv6, но и чтение, и обучение идут в самом kraken, PaddleOCR не нужен.

Мы дообучили её в два шага:

1. 2 112 строк Минеи сентябрьской (Киев, 1893; скан с archive.org). В обучение шли только строки, текст которых совпал с набором этой Минеи в [cu-md-sandbox](https://github.com/slavonic/cu-md-sandbox) (без учёта переносов и знака ꙳); совпала почти половина.
2. 2 319 строк из обучающей части набора church-slavonic-ocr А. Андреева (версия 16ba0a9, лицензия MIT), из тех же 7 книг, с нашими исправлениями эталона.

## In English

A [kraken](https://kraken.re) recognition model for Church Slavonic books in the Synodal typeface (tested on books printed 1893–2021), with accents, breathings and titlos, made by the Slovesitsa project ([slovesitsa.org](https://slovesitsa.org)). Tested with kraken 7.1.1 (Python 3.10–3.13):

```
pip install kraken==7.1.1
kraken -i page.png page.txt segment -bl ocr -m cu_synodal_v1.safetensors
```

The output is decomposed Unicode (NFD). `to_andreev.py` converts it to the notation of A. Andreev's church-slavonic-ocr (NFC, "ᲂу", "_"); only the notation changes. CER 1.09 % on the 269 ready-cut test lines of church-slavonic-ocr (version 16ba0a9 with the 48 ground-truth corrections we sent him; functions of his `cu_eval.py`, after `to_andreev.py`; 4.98 % without it); his Tesseract model: 5.69 % on the same lines. Fine-tuned from Benjamin Kiessling's PP-OCRv6 medium (Apache 2.0) on 2,112 lines of the Kiev 1893 September Menaion (only lines whose text matched the cu-md-sandbox edition) and 2,319 training lines of church-slavonic-ocr. Weak spots: 1-bit scans, red print, accents on some books. Not tested on civil script, Greek, pre-Nikonian books or manuscripts. Apache 2.0; see NOTICE.
