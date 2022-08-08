<div align="center">
  <a href="https://github.com/furkanonder/eksigundem/actions"><img alt="Actions Status" src="https://github.com/furkanonder/eksigundem/workflows/Test/badge.svg"></a>
  <a href="https://github.com/furkanonder/eksigundem/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/furkanonder/eksigundem"></a>
  <a href="https://github.com/furkanonder/eksigundem/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/furkanonder/eksigundem"></a>
  <a href="https://github.com/furkanonder/eksigundem/blob/main/LICENSE"><img alt="GitHub license" src="https://img.shields.io/github/license/furkanonder/eksigundem"></a>
  <a href="https://pepy.tech/project/eksi"><img alt="Downloads" src="https://pepy.tech/badge/eksi"></a>
</div>

# EkşiGündem

Turkish is the only language available on the [ekisozluk.com](https://eksisozluk.com/),
so the readme file is written in Turkish. In a nutshell, the project helps you browse
popular trending topics and read them on the command line.

Ekşi Gündem, komut satırından [Ekşi Sözlük'ün](https://eksisozluk.com/) gündem
başlıklarını ve entrylerini okumanıza yarayan bir araçtır.

# Kurulum

Python paket yöneticisi ile kolayca kurabilirsiniz.

```python
pip install eksi
```

Paket yöneticisi olmadan, bu şekilde de kurabilirsiniz.

```python
python setup.py install
```

# Çalıştırma

Terminalinize

```bash
eksi
```

yazarak kullanabilirsiniz. Ek olarak, -b parametresini kullanarak okumak istediğiniz
başlık sayısını belirtebilirsiniz.

```bash
eksi -b 10
```
