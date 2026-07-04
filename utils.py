from datetime import date, datetime, timedelta


def parse_deadline(text: str) -> date:
    """Позволяет ввести срок двумя способами:
    - числом дней от сегодня, например "5"
    - датой в формате 31.12.2026 / 31.12.26 / 31-12-2026
    """
    text = text.strip()
    if not text:
        raise ValueError("Укажите срок")

    if text.isdigit():
        return date.today() + timedelta(days=int(text))

    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise ValueError("Не понял срок. Введите число дней (напр. 5) или дату 31.12.2026")
