# Reestr parser
This is small util, to parse data from report exported from Rosreestr and [Domovoi telegram bot](https://t.me/damavikbot) to more readable format. Tested on files for Discovery Park. 
## Requiremnts
- Python >= 3.6
- [Transliterate](https://pypi.org/project/transliterate/) - package for transliterates string.
Installation: `pip install transliterate`
- [PyMuPDF](https://pypi.org/project/PyMuPDF/) - package for working with PDF files.
Installation: `pip install PyMuPDF`
- [Progress](https://pypi.org/project/progress/) - just a progress bar :)
Installation: `pip install progress`
## Usage example
Run command in termina
`python parseReestr.py report.pdf domovoi_report.csv`
Where 1st argument - ros reestr report, 2nd argument - report exported from Domovoi bot