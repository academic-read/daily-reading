from pydantic import BaseModel, Field, field_validator
import re


class BSchoolPaperStructure(BaseModel):
    tldr: str = Field(description="generate a too long; didn't read summary")
    research_question: str = Field(description="research question of this paper")
    motivation: str = Field(description="motivation of this paper")
    theoretical_framework: str = Field(description="key theories of this paper")
    method: str = Field(description="method of this paper")
    findings: str = Field(description="results of this paper")
    theory_contributions: str = Field(description="theoretical contributions of this paper")
    practical_contributions: str = Field(description="practical contributions of this paper")
