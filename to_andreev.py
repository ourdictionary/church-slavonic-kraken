#!/usr/bin/env python3
"""Перевод выхода модели в запись набора church-slavonic-ocr А. Андреева (и его библиотеки cu-md-sandbox).
Меняется только запись тех же знаков, прочитанное не правится:
1) составной Юникод (NFC) вместо разложенного (NFD), в котором пишет модель;
2) строчное «оу» → «ᲂу» (U+1C82 U+0443);
3) дефисы и тире → «_» (так в его эталоне записан любой разделитель).
Запуск: python3 to_andreev.py page.txt > page_cu.txt

Converts the model output to the notation of A. Andreev's church-slavonic-ocr: NFC, lowercase "оу" -> "ᲂу", dashes -> "_".
"""
import re
import sys
import unicodedata

DASH = re.compile(r"[-‐‑‒–—―]")


def convert(text):
    text = unicodedata.normalize("NFD", " ".join(text.split())).replace("оу", "ᲂу")
    return unicodedata.normalize("NFC", DASH.sub("_", text))


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        for line in f:
            print(convert(line))
