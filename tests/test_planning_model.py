"""Tests for the shared planning model and the curriculum adapter."""

from __future__ import annotations

import json

import pytest

from backend.models import (
    NOT_TAKEN,
    PrerequisiteParseError,
    load_curriculum,
    parse_prerequisites,
    problem_from_curriculum,
)


def test_parser_matches_pair_a_tree_shape():
    parsed = parse_prerequisites("CS F211 AND (MATH F211 OR MATH F213)")
    assert parsed == {
        "kind": "and",
        "items": [
            {"kind": "leaf", "course": "CS F211", "relation": "PRE"},
            {
                "kind": "or",
                "items": [
                    {"kind": "leaf", "course": "MATH F211", "relation": "PRE"},
                    {"kind": "leaf", "course": "MATH F213", "relation": "PRE"},
                ],
            },
        ],
    }
    assert parse_prerequisites("BIO F341:CO") == {
        "kind": "leaf",
        "course": "BIO F341",
        "relation": "CO",
    }
    assert parse_prerequisites(None) is None
    assert parse_prerequisites("") is None


def test_parser_rejects_mixed_and_or_without_parentheses():
    with pytest.raises(PrerequisiteParseError):
        parse_prerequisites("CS F111 AND CS F211 OR CS F222")


def test_problem_from_curriculum_maps_parity_and_requirements(tmp_path):
    common = tmp_path / "common"
    branch = tmp_path / "branches" / "cse"
    common.mkdir()
    branch.mkdir(parents=True)
    (common / "courses.json").write_text(
        json.dumps(
            [
                {
                    "code": "CS F111",
                    "title": "Intro",
                    "credits": 4,
                    "term_parity": "both",
                    "category": "University Core (First Year)",
                    "prerequisites": None,
                }
            ]
        ),
        encoding="utf-8",
    )
    (branch / "courses.json").write_text(
        json.dumps(
            [
                {
                    "code": "CS F213",
                    "title": "OOP",
                    "credits": 4,
                    "term_parity": "odd",
                    "category": "Discipline Core",
                    "prerequisites": "CS F111",
                }
            ]
        ),
        encoding="utf-8",
    )
    (branch / "requirements.json").write_text(
        json.dumps(
            [
                {
                    "category": "Discipline Core",
                    "credit_minimum": 4,
                    "eligible_courses": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    curriculum = load_curriculum(tmp_path, branch="cse")
    problem = problem_from_curriculum(
        curriculum,
        completed={"CS F111"},
        current_semester=2,
        target_semester=5,
        max_credits=20,
    )

    assert problem.courses["CS F111"]["parity"] is None
    assert problem.courses["CS F213"]["parity"] == "odd"
    assert problem.courses["CS F213"]["formula"] == {
        "kind": "leaf",
        "course": "CS F111",
        "relation": "PRE",
    }
    assert problem.variables == ["CS F213"]
    assert problem.initial_domains()["CS F213"] == [3, 5]
    assert NOT_TAKEN not in problem.initial_domains()["CS F213"]
    assert problem.category_minimums["Discipline Core"] == 4
    assert "prereq:CS F213" in problem.named_constraints()
