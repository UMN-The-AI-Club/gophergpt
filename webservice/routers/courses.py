from fastapi import APIRouter
from autonomy.tools.gophergrades_api import fetch_search, fetch_class, fetch_dept
from pydantic import BaseModel

from autonomy.tools.umn_courses_tool import fetch_sections

import json
import statistics
import re

router = APIRouter()

KNOWN_REQUIRED_DEPT_COURSES = {
    "CSCI": {"1133", "1913", "1933", "2011", "2021", "2033", "2041", "4041"},
    "MATH": {"1271", "1272", "1371", "1372", "1571", "1572", "2243", "2263", "2373", "2374", "3283W"},
    "STAT": {"3011", "3021", "3032", "5101"},
    "BIOL": {"1951", "1961", "2003", "2004"},
    "CHEM": {"1015", "1061", "1062", "2301", "2302"},
    "PHYS": {"1301W", "1302W", "1401V", "1402V"},
}

def _course_level(course_num):
    match = re.match(r"(\d{4})", str(course_num))
    if not match:
        return None
    return int(match.group(1))

def _is_popular_elective_candidate(course, dept_code):
    course_num = str(course.get("course_num") or "").upper()
    title = str(course.get("title") or "").lower()
    description = str(course.get("description") or "").lower()
    level = _course_level(course_num)
    combined = f"{title} {description}"

    if level is None or level < 3000:
        return False
    if course_num in KNOWN_REQUIRED_DEPT_COURSES.get(dept_code, set()):
        return False

    core_hints = (
        "introduction to", "intro to", "foundations", "fundamentals",
        "elementary", "principles", "basic ", "corequisite", "required",
    )
    if any(hint in combined for hint in core_hints):
        return False

    return True

class SectionsLookupRequest(BaseModel):
    """Request model for course section lookup."""
    subject: str
    catalog_number: str
    term: str

class CourseLookupRequest(BaseModel):
    """Request model for course lookup endpoint."""
    query: str

class ProfessorLookupRequest(BaseModel):
    """Request model for professor lookup endpoint."""
    name: str

class DepartmentLookupRequest(BaseModel):
    """Request model for department lookup endpoint."""
    dept: str

def _parse_srt_vals(raw):
    """
    Parses raw SRT values into a dict.

    Args:
        raw: raw SRT value from GopherGrades, can be None, a dict, or a JSON string

    Returns:
        a dict of SRT values, or None if unparseable
    """
    if raw is None or raw == "null":
        return None

    if isinstance(raw, dict):
        return raw

    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def _sum_grade_counts(grades):
    """
    Sums all numeric grade counts from a grades dict.

    Args:
        grades: dict of grade letters to counts (e.g. {"A": 10, "B": 5})

    Returns:
        total number of graded outcomes as an integer
    """
    if not grades:
        return 0

    return sum(value for value in grades.values() if isinstance(value, (int, float)))


def _compute_course_metrics(course):
    """
    Computes derived metrics for a course from its grade and SRT data.

    Args:
        course: raw course dict from GopherGrades API

    Returns:
        a dict of computed metrics including high_grade_rate, challenge_rate, and SRT values
    """
    grades = course.get("total_grades") or {}
    total_outcomes = _sum_grade_counts(grades)
    srt_vals = _parse_srt_vals(course.get("srt_vals"))

    recommend = srt_vals.get("RECC") if srt_vals else None
    responses = srt_vals.get("RESP") if srt_vals else None

    high_grade_rate = None
    challenge_rate = None
    withdraw_rate = None

    if total_outcomes > 0:
        high_grade_rate = (
            grades.get("A", 0) + grades.get("A-", 0) + grades.get("B+", 0)
        ) / total_outcomes
        challenging_count = (
            grades.get("C-", 0)
            + grades.get("D+", 0)
            + grades.get("D", 0)
            + grades.get("F", 0)
            + grades.get("W", 0)
            + grades.get("N", 0)
        )
        # Bayesian smoothing: blend observed rate toward a prior (7%) weighted
        # by 100 pseudo-students. Small classes get pulled toward the prior;
        # large classes are barely affected.
        _PRIOR_RATE = 0.07
        _PRIOR_WEIGHT = 100
        challenge_rate = (challenging_count + _PRIOR_WEIGHT * _PRIOR_RATE) / (total_outcomes + _PRIOR_WEIGHT)
        withdraw_rate = grades.get("W", 0) / total_outcomes

    return {
        "recommend": recommend,
        "responses": responses,
        "deep_understanding": srt_vals.get("DEEP_UND") if srt_vals else None,
        "stimulating_interest": srt_vals.get("STIM_INT") if srt_vals else None,
        "technical_effectiveness": srt_vals.get("TECH_EFF") if srt_vals else None,
        "accessible_support": srt_vals.get("ACC_SUP") if srt_vals else None,
        "effort": srt_vals.get("EFFORT") if srt_vals else None,
        "grading_standards": srt_vals.get("GRAD_STAND") if srt_vals else None,
        "high_grade_rate": high_grade_rate,
        "challenge_rate": challenge_rate,
        "withdraw_rate": withdraw_rate,
    }


def _normalize_department_course(course):
    """
    Normalizes a raw GopherGrades course dict into a clean frontend-ready format.

    Args:
        course: raw course dict from GopherGrades API

    Returns:
        a normalized course dict with consistent field names and structure
    """
    return {
        "id": course.get("id"),
        "course_num": course.get("course_num", ""),
        "title": course.get("class_desc", ""),
        "description": course.get("onestop_desc", ""),
        "catalog_url": course.get("onestop", ""),
        "credits": {
            "min": course.get("cred_min"),
            "max": course.get("cred_max"),
        },
        "total_students": course.get("total_students", 0),
        "grades": course.get("total_grades") or {},
        "metrics": _compute_course_metrics(course),
    }


def _build_department_summary(courses):
    """
    Builds aggregate summary statistics for a list of courses.

    Args:
        courses: list of normalized course dicts

    Returns:
        a dict containing course count, total students, median course size, and avg recommend score
    """
    student_counts = [course.get("total_students", 0) for course in courses]
    recommend_values = [
        course["metrics"]["recommend"]
        for course in courses
        if course["metrics"]["recommend"] is not None
    ]

    return {
        "course_count": len(courses),
        "total_students": sum(student_counts),
        "median_course_size": int(statistics.median(student_counts)) if student_counts else 0,
        "courses_with_srt": len(recommend_values),
        "avg_recommend": (
            round(sum(recommend_values) / len(recommend_values), 3)
            if recommend_values
            else None
        ),
    }


def _build_department_featured(courses, dept_code=""):
    popular = sorted(
        courses,
        key=lambda course: course.get("total_students", 0),
        reverse=True,
    )[:8]

    best_rated_pool = [
        course
        for course in courses
        if course["metrics"]["recommend"] is not None
        and (course["metrics"]["responses"] or 0) >= 50
    ]
    best_rated = sorted(
        best_rated_pool,
        key=lambda course: (
            course["metrics"]["recommend"],
            course["metrics"]["responses"] or 0,
        ),
        reverse=True,
    )[:8]

    elective_pool = [
        course for course in courses
        if _is_popular_elective_candidate(course, dept_code)
    ]
    popular_electives = sorted(
        elective_pool,
        key=lambda course: (
            course.get("total_students", 0),
            course["metrics"]["recommend"] or 0,
        ),
        reverse=True,
    )[:8]

    return {
        "popular": popular,
        "best_rated": best_rated,
        "popular_electives": popular_electives,
    }

@router.post("/umn/course")
def lookup_course(request: CourseLookupRequest):
    """
    Looks up a UMN course by query string, returning search results and full class data if a course code is detected.

    Args:
        request: CourseLookupRequest containing the query string

    Returns:
        a dict with ok status, search results, and class data if found
    """
    query = request.query.strip()

    try:
        search_result = fetch_search(request.query)

        response = {
            "ok": True,
            "query": query,
            "search": search_result,
            "class": None
        }

        normalized = query.replace(" ", "").upper()

        if re.match(r"^[A-Z]{2,}\d{4}$", normalized):
            class_result = fetch_class(normalized)
            response["class"] = class_result

        return response

    except Exception as e:
        return {
            "ok": False,
            "query": query,
            "error": str(e)
        }


@router.post("/umn/prof")
def lookup_professor(request: ProfessorLookupRequest):
    """
    Looks up a UMN professor by name using GopherGrades search.

    Args:
        request: ProfessorLookupRequest containing the professor name

    Returns:
        a dict with ok status and search results
    """
    name = request.name.strip()

    try:
        search_result = fetch_search(name)

        return {
            "ok": True,
            "name": name,
            "search": search_result
        }

    except Exception as e:
        return {
            "ok": False,
            "name": name,
            "error": str(e)
        }


@router.post("/umn/dept")
def lookup_department(request: DepartmentLookupRequest):
    """
    Looks up a UMN department by code, returning summary, featured courses, and full course list.

    Args:
        request: DepartmentLookupRequest containing the department code

    Returns:
        a dict with ok status, department info, summary, featured courses, and full course list
    """
    dept = request.dept.strip().upper()

    try:
        raw_result = fetch_dept(dept)

        if not raw_result.get("success") or not raw_result.get("data"):
            return {
                "ok": False,
                "dept": dept,
                "error": "Department not found."
            }

        data = raw_result["data"]
        normalized_courses = [
            _normalize_department_course(course)
            for course in data.get("distributions", [])
        ]

        return {
            "ok": True,
            "dept": {
                "campus": data.get("campus"),
                "code": data.get("dept_abbr"),
                "name": data.get("dept_name"),
            },
            "summary": _build_department_summary(normalized_courses),
            "featured": _build_department_featured(normalized_courses, dept),
            "courses": normalized_courses,
        }

    except Exception as e:
        return {
            "ok": False,
            "dept": dept,
            "error": str(e)
        }


@router.post("/umn/sections")
def lookup_sections(request: SectionsLookupRequest):
    try:
        result = fetch_sections(request.subject, request.catalog_number, request.term)
        return {"ok": True, "sections": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}