# -*- coding: utf-8 -*-
"""学习卡片（从原 StudyCardSystem 迁移，间隔重复）。"""

from datetime import datetime

from core.database import Database


class CardSystem:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db = Database()

    def add_card(self, title: str, answer: str, question: str = "",
                 category: str = "通用", tags: str = "") -> int:
        cur = self.db.execute(
            """INSERT INTO study_cards
               (session_id, title, question, answer, category, tags, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (self.session_id, title, question, answer, category, tags,
             datetime.now().isoformat()))
        self.db.commit()
        return cur.lastrowid

    def get_cards(self, category: str = "") -> list[dict]:
        if category:
            return self.db.fetchall(
                "SELECT * FROM study_cards WHERE session_id=? AND category=? ORDER BY difficulty DESC, review_count ASC",
                (self.session_id, category))
        return self.db.fetchall(
            "SELECT * FROM study_cards WHERE session_id=? ORDER BY difficulty DESC, review_count ASC",
            (self.session_id,))

    def get_categories(self) -> list[str]:
        rows = self.db.fetchall(
            "SELECT DISTINCT category FROM study_cards WHERE session_id=?",
            (self.session_id,))
        return [r["category"] for r in rows if r["category"]]

    def delete_card(self, card_id: int):
        self.db.execute("DELETE FROM study_cards WHERE id=?", (card_id,))
        self.db.commit()

    def review_card(self, card_id: int, difficulty: int):
        """difficulty 1(简单)/3(一般)/5(困难)，更新复习次数与难度。"""
        self.db.execute(
            "UPDATE study_cards SET review_count=review_count+1, difficulty=?, "
            "category=category WHERE id=?",
            (difficulty, card_id))
        self.db.commit()
