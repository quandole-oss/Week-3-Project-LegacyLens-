"""Prompt templates for LLM generation."""

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are LegacyLens, an expert assistant for understanding legacy Fortran codebases, specifically LAPACK (Linear Algebra PACKage).

Your role is to help developers understand, document, and work with legacy Fortran code. You should:

1. Only answer based on the provided source code context. If the context doesn't contain enough information, say so.
2. Always cite specific file paths and line numbers when referencing code.
3. Explain Fortran conventions (IMPLICIT types, column formatting, COMMON blocks) when relevant.
4. Use clear, modern terminology to explain legacy patterns.
5. When discussing algorithms, explain both what the code does and why (the mathematical purpose).

Format your responses with markdown for readability. Use code blocks with `fortran` syntax highlighting for code snippets."""

QUERY_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Based on the following LAPACK source code context, answer the question.

## Source Code Context
{context}

## Question
{question}

Provide a clear, detailed answer citing specific files and line numbers from the context above."""),
])

EXPLAIN_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Explain the following Fortran routine in detail.

## Source Code
{context}

Provide:
1. **Purpose**: What this routine does in plain English
2. **Algorithm**: The mathematical/computational approach used
3. **Parameters**: Input/output parameters and their meanings
4. **Key Implementation Details**: Important Fortran-specific patterns or optimizations
5. **Usage**: When and why you would call this routine"""),
])

DOCGEN_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Generate comprehensive documentation for the following Fortran routine.

## Source Code
{context}

Generate documentation in the following format:
1. **Summary**: One-line description
2. **Description**: Detailed explanation of purpose and algorithm
3. **Parameters**: Table of all parameters with types, intent (in/out/inout), and descriptions
4. **Returns**: What the routine returns or modifies
5. **Notes**: Any important implementation details, numerical considerations, or usage caveats
6. **Example Usage**: A brief example of how this routine would be called"""),
])

BUSINESS_LOGIC_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Extract and explain the business logic / mathematical algorithm encoded in this Fortran routine.

## Source Code
{context}

Provide:
1. **Mathematical Operation**: What mathematical operation this implements (e.g., LU decomposition, QR factorization)
2. **Algorithm Steps**: Step-by-step explanation of the algorithm in plain English
3. **Numerical Considerations**: Precision, stability, and edge case handling
4. **Real-World Applications**: Where this algorithm is used in practice
5. **Complexity**: Time and space complexity"""),
])
