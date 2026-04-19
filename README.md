# EkşiGündem

[![Actions Status](https://github.com/furkanonder/eksigundem/workflows/Test/badge.svg)](https://github.com/furkanonder/eksigundem/actions)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/eksi)](https://pypi.org/project/eksi/)
[![PyPI](https://img.shields.io/pypi/v/eksi)](https://pypi.org/project/eksi/)
[![Downloads](https://pepy.tech/badge/eksi)](https://pepy.tech/project/eksi)
[![License](https://img.shields.io/github/license/furkanonder/eksigundem)](https://github.com/furkanonder/eksigundem/blob/main/LICENSE)


Turkish is the only language available on the [eksisozluk.com](https://eksisozluk.com/),
so the README is written in Turkish. In a nutshell, this CLI tool helps you browse
popular trending topics and read entries from Ekşi Sözlük on the command line.

Ekşi Gündem, komut satırından [Ekşi Sözlük'ün](https://eksisozluk.com/) gündem
başlıklarını ve entrylerini okumanıza yarayan bir araçtır.

## Kurulum

Python 3.10 veya üzeri gereklidir.

```bash
pip install eksi
```

## Kullanım

Terminalinize `eksi` yazarak başlatabilirsiniz:

```bash
eksi
```

### Parametreler

| Parametre               | Açıklama                                          |
|-------------------------|---------------------------------------------------|
| `-b`, `--baslik_sayisi` | Gösterilecek başlık sayısı (varsayılan: 10)       |
| `-v`, `--versiyon`      | Sürüm bilgisini gösterir                          |


### Tuş Kısayolları

| Tuş                   | Eylem                 |
|-----------------------|-----------------------|
| `Enter`               | 1 satır aşağı kaydır  |
| `Space`               | Sayfa aşağı           |
| `↑` (yukarı yön tuşu) | 1 satır yukarı kaydır |
| `↓` (aşağı yön tuşu)  | 1 satır aşağı kaydır  |
| `Home`                | Sayfa başına git      |
| `End`                 | Sayfa sonuna git      |
| `Page Up`             | Sayfa yukarı          |
| `Page Down`           | Sayfa aşağı           |
| `i`                   | İlk sayfa             |
| `o`                   | Önceki sayfa          |
| `s`                   | Sonraki sayfa         |
| `e`                   | En son sayfa          |
| `g`                   | Gündem listesine dön  |
| `Ctrl+C`              | Çıkış                 |

## Değişiklik Günlüğü

Tüm değişiklikler için [CHANGELOG.md](CHANGELOG.md) dosyasına bakın.

## Lisans

[MIT](LICENSE)
