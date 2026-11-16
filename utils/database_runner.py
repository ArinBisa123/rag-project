from datetime import datetime
from langchain_core.messages import HumanMessage

def run_database_tools(
    user_question,
    tool_model,
    tool_map
):

    current_year = datetime.now().year

    routing_message = HumanMessage(
        content=f"""
Current year: {current_year}

Analyze the user's question and decide whether
SQL Server data is required.

Available SQL Server data:
- Employee profiles
- Medical claim transactions
- Claim totals

Rules:
1. Call database tools only when the question
   requires employee or transaction facts.
2. Do not call database tools for general company
   policy questions.
3. Do not invent Employee IDs.
4. If the user says "tahun ini",
   use {current_year}.
5. If the user says "tahun lalu",
   use {current_year - 1}.
6. Employee IDs follow a pattern such as EMP0008.

User question:
{user_question}
"""
    )

    planning_response = tool_model.invoke(
        [routing_message]
    )

    if not planning_response.tool_calls:
        return (
            "No database lookup was required "
            "for this question."
        )

    context_parts = []

    for tool_call in planning_response.tool_calls:

        tool_name = tool_call["name"]
        tool_arguments = tool_call["args"]

        selected_tool = tool_map.get(tool_name)

        if selected_tool is None:
            context_parts.append(
                f"Unknown database tool: {tool_name}"
            )
            continue

        try:
            tool_result = selected_tool.invoke(
                tool_arguments
            )

            tool_context = "\n".join([
                f"Database tool: {tool_name}",
                f"Arguments: {tool_arguments}",
                "Result:",
                str(tool_result),
            ])

            context_parts.append(
                tool_context
            )

        except Exception as error:

            error_context = "\n".join([
                f"Database tool: {tool_name}",
                f"Arguments: {tool_arguments}",
                "Execution failed:",
                (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            ])

            context_parts.append(
                error_context
            )
    return "\n\n".join(context_parts)