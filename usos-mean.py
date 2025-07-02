#!/usr/bin/env python3
import PyPDF2
import re
import argparse

# Wzorzec regex
line_pattern = re.compile(r"[a-z]\s+\d+\s+\d+,\d+\s+\d+\s+$")
code_pattern = re.compile(r"^\(.*\) ")
hours_pattern = re.compile(r"[a-z]\s+\d{2,}\s+")
multiline_subject_name_pattern = re.compile(r"([A-Z0-9]+-\w+)")
no_ects_pattern = re.compile(r"[a-z]\s+\d+\s+\d+,\d+\s+$")

NAME_WIDTH = 75
GRADE_WIDTH = 6
ECTS_WIDTH = 5


class subject:
    def __init__(self, name, grade, ects):
        self.name = name
        self.grade = grade
        self.ects = ects

    def print_row(self):
        print(
            f"| {str(self.name).center(NAME_WIDTH)} | {str(self.grade).center(GRADE_WIDTH)} | {str(self.ects).center(ECTS_WIDTH)} |"
        )


class semester:
    def __init__(self, subjects_list):
        self.subjects = subjects_list
        self.ects_sum = 0
        self.mean = 0

        for subject in self.subjects:
            self.ects_sum += subject.ects

        numerator = 0
        for subject in self.subjects:
            numerator += subject.grade * subject.ects
        self.mean = numerator / self.ects_sum

    def print_semester(self):
        print(
            f"| {'Nazwa przedmiotu'.center(NAME_WIDTH)} | {'Ocena'.center(GRADE_WIDTH)} | {'ECTS'.center(ECTS_WIDTH)} |"
        )
        print(f"| {'-'*NAME_WIDTH} | {'-'*GRADE_WIDTH} | {'-'*ECTS_WIDTH} |")
        for subject in self.subjects:
            subject.print_row()
        mean_text = f"{self.mean:.3f}"
        print(
            f"| {'Podsumowanie semestru'.rjust(NAME_WIDTH)} | {mean_text.ljust(GRADE_WIDTH)} | { str(self.ects_sum).center(ECTS_WIDTH) } |"
        )
        print(f"| {'-'*NAME_WIDTH} | {'-'*GRADE_WIDTH} | { '-'*ECTS_WIDTH } |")

    def get_grades(self):
        grades = []
        for subject in self.subjects:
            grades.append(subject.grade)
        return grades

    def get_ects(self):
        ects = []
        for subject in self.subjects:
            ects.append(subject.ects)
        return ects


class years:
    def __init__(self, semesters):
        self.semesters = semesters
        self.ects_sum = 0
        self.mean = 0

        for semester in self.semesters:
            self.ects_sum += semester.ects_sum

        numerator = 0
        grades = []
        ects = []
        for semester in self.semesters:
            grades += semester.get_grades()
            ects += semester.get_ects()
        for idx, grade in enumerate(grades):
            numerator += grade * ects[idx]
        self.mean = numerator / self.ects_sum

    def print_year(self):
        table_width = NAME_WIDTH + GRADE_WIDTH + ECTS_WIDTH
        mean_text = f"{self.mean:.3f}"
        for num, semestr in enumerate(self.semesters):
            semestr.print_semester()
        print(
            f"| {'Podsumowanie roku'.rjust(NAME_WIDTH)} | {mean_text.center(GRADE_WIDTH)} | {str(self.ects_sum).center(ECTS_WIDTH)} |"
        )


def read_pdf(pdfname):
    with open(pdfname, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        start_reading = False  # Flaga do kontroli, kiedy zacząć odczytywać tekst
        # Przejdź przez każdą stronę
        return_lines = []
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()

            # Podziel tekst na linijki
            lines = text.splitlines()

            for line in lines:
                # Sprawdź, czy linijka to nasz znacznik początkowy
                if (
                    "Przedmioty wg cykli dydaktycznych Zajęcia/godziny Ocena ECTS"
                    in line
                ):
                    start_reading = True  # Ustaw flagę na True, aby zacząć odczytywać
                    continue  # Pomijamy samą linię znacznika
                elif "Razem ECTS:" in line:
                    start_reading = False

                # Jeśli flaga jest ustawiona, odczytuj linijki
                if (
                    start_reading
                    and not line.startswith("Strona")
                    and not line.startswith("USOSweb: Karta przebiegu studiów")
                ):
                    return_lines.append(line)
        return return_lines


def prepare_semestr_list(pdf_text):
    semestr_list = []
    text = ""
    for line in pdf_text:
        if line.startswith("Semestr"):
            if not line in semestr_list:
                semestr_list.append(line)
                text += "Semestr\n"
        elif (
            multiline_subject_name_pattern.search(line)
            and not no_ects_pattern.search(line)
            and not line_pattern.search(line)
        ):
            line = re.sub(code_pattern, "", line)
            line = re.sub(hours_pattern, "", line)
            line = re.sub(r"\s+", " ", line)
            text += line
        elif line_pattern.search(line):
            line = re.sub(code_pattern, "", line)
            line = re.sub(hours_pattern, "", line)
            line = re.sub(r"\s+", " ", line)
            text += line + "\n"

    text = text.split("Semestr")
    text = [semester.strip() for semester in text if semester.strip()]
    return text


def write_subjects(text):
    ects_pattern = re.compile(r"\d+\s?$")
    grade_pattern = re.compile(r"\d+,\d+\s$")
    subject_list = []
    for line in text.splitlines():
        ects = int(re.search(ects_pattern, line).group())
        line = re.sub(ects_pattern, "", line)
        grade = re.search(grade_pattern, line).group()
        grade = float(grade.replace(",", "."))
        line = re.sub(grade_pattern, "", line)
        line = re.sub(r"(\s$)|(^\s)", "", line)
        name = line.replace("\n", "")
        subject_list.append(subject(name, grade, ects))
        # print(f"Przedmiot o nazwie: {name}, ocena {grade}, ects: {ects}")
    return subject_list


def setup_semester(pdfname):
    semesters = []
    pdf_text = read_pdf(pdfname)
    semesters_text = prepare_semestr_list(pdf_text)
    for semester_text in semesters_text:
        subjects = write_subjects(semester_text)
        semesters.append(semester(subjects))
    return semesters


def setup_years(semesters):
    semester_count = len(semesters)
    year_count = 0
    years_list = []

    for num in range(int(semester_count / 2)):
        years_list.append(years([semesters[2 * num], semesters[2 * num + 1]]))

    if semester_count % 2 == 1:
        years_list.append(years([semesters[semester_count - 1]]))

    return years_list


def print_years(years):
    table_width = NAME_WIDTH + GRADE_WIDTH + ECTS_WIDTH
    for num, year in enumerate(years):
        year_text = "Rok " + str(num + 1)
        print(f"| {'-'*(table_width+6)} |")
        print(f"| {year_text.center(NAME_WIDTH)} {' '*(GRADE_WIDTH+ECTS_WIDTH+5)} |")
        print(f"| {'-'*(table_width+6)} |")
        year.print_year()


# Tworzymy parser argumentów
parser = argparse.ArgumentParser(
    description="Program przyjmuje jeden obowiązkowy argument: --file"
)

# Dodajemy obowiązkowe argumenty
parser.add_argument(
    "-f", "--file", required=True, type=str, help="Podaj ścieżke do pliku pdf"
)

# Parsujemy argumenty
args = parser.parse_args()

pdfname = args.file

semesters = setup_semester(pdfname)
years = setup_years(semesters)


print_years(years)
