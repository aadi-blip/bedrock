from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arxiv_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[str | None] = mapped_column(Text)  # JSON array
    year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    seed: Mapped[bool] = mapped_column(Boolean, default=False)
    digest: Mapped[str | None] = mapped_column(Text, nullable=True)
    digest_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    crawled: Mapped[bool] = mapped_column(Boolean, default=False)
    crawl_depth: Mapped[int | None] = mapped_column(Integer)
    gap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_frontier: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    outgoing_edges: Mapped[list["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.source_id", back_populates="source"
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.target_id", back_populates="target"
    )


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (UniqueConstraint("source_id", "target_id", name="uq_edge_source_target"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source: Mapped["Paper"] = relationship("Paper", foreign_keys=[source_id], back_populates="outgoing_edges")
    target: Mapped["Paper"] = relationship("Paper", foreign_keys=[target_id], back_populates="incoming_edges")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arxiv_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)  # pending / running / done / error
    depth: Mapped[int] = mapped_column(Integer)
    papers_found: Mapped[int] = mapped_column(Integer, default=0)
    edges_found: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
