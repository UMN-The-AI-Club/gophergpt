import re

def check_tool_leak(response: str) -> str:
    """
    Checks the response for any mention of tools

    Args:
        response: the response from agent, before showing user

    Returns:
        removes any mention of tool names, while maintaining existing string and structure.
    """

    tool_list = ["gophergrades_search", 
                "gophergrades_class", 
                "gophergrades_prof", 
                "gophergrades_dept", 
                "umn_class_sections", 
                "umn_room_booking", 
                "course_search", 
                "rag_search", 
                "tavily_search"]

    sentences = re.split(r'(?<=[.!?])\s+', response)
    filtered = [s for s in sentences if not any(filler.lower() in s.lower() for filler in tool_list)]
    response = " ".join(filtered)

    return response


def check_filler(response: str) -> str:
    """
    Checks the response for filler words

    Args:
        response: the response from agent, before showing user

    Returns:
        stripped response with filler phrases removed, 
        or the original response unchanged if none are found.
    """

    filler_list = ["Don't hesitate to reach out",
                   "I hope this helps",
                   "Is there anything else I can help you with",
                   "let me know",
                   "feel free"]
    
    sentences = re.split(r'(?<=[.!?])\s+', response)
    filtered = [s for s in sentences if not any(filler.lower() in s.lower() for filler in filler_list)]
    response = " ".join(filtered)

    return response

# may be deprecated 
# def check_prof_rating(response: str, message: str) -> str:
#     """
#     Checks the message for mentions of professor

#     Args:
#         response: the response from agent, before showing user
#         message: the query from the user

#     Returns:
#         the original response unchanged if a rating is found or the question isn't about a professor, 
#         else a fallback message prompting the user to ask more specifically.
#     """

#     prof_keywords = ["professor", "prof", "instructor", "teacher", "who teaches"]

#     for keyword in prof_keywords:
#         if keyword in message.lower():
#             if not re.search(r'\d+\.?\d*/5', response):
#                 return "I wasn't able to find a rating for that professor. " \
#                 "Try asking about a specific professor by name."
        
#     return response


def run_guardrails(response: str, message: str) -> str:
    """
    Runs all guardrail checks on the agent response in sequence. 
    Returns the cleaned response or a fallback message if any check fails.

    Args:
        response: the response from agent, before showing user
        message: the query from the user

    Returns:
        the cleaned response or a fallback message if any check fails.    
    """
    response = check_tool_leak(response)
    response = check_filler(response)
    # response = check_prof_rating(response, message)


    return response