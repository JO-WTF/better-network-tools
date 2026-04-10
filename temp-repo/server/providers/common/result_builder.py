def success_result(**kwargs):
    return {"success": True, **kwargs}


def error_result(error_type, request, response):
    return {
        "success": False,
        "errorType": error_type,
        "request": request,
        "response": response,
    }
