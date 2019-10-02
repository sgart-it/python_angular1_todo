# services.py
from flask import request
import pyodbc
import json
from datetime import datetime


# load config


def __get_config():
    with open('config.json') as json_data_file:
        return json.load(json_data_file)


__config = __get_config()

# db common


def __db_get_connection():
    db = __config["db"]
    connection_string = "DRIVER={};SERVER={};DATABASE={};UID={};PWD={}".format(
        db["driver"], db["server"], db["database"], db["username"], db["password"])
    return pyodbc.connect(connection_string)


def __db_get_cursor(cnn, query, params=()):
    cursor = cnn.cursor()
    cursor.execute(query, params)
    return cursor


def ___db_execute_cursor(query, params=()):
    with __db_get_connection() as cnn:
        cursor = cnn.cursor()
        cursor.execute(query, params)
        cnn.commit()


# service status


def service_status_get(data=None):
    return {"success": False, "data": data, "returnValue": 0, "messages": []}


def service_status_get_message(types, message, seconds):
    return {"t": types, "m": message, "s": seconds}


def service_status_add_error(result, message):
    result["messages"].append({"t": "E", "m": message, "s": 30})


def service_status_add_warnig(result, message):
    result["messages"].append({"t": "W", "m": message, "s": 15})


def service_status_add_success(result, message):
    result["messages"].append({"t": "S", "m": message, "s": 1.5})


# query
queries = {
    "search": "EXEC spu_todos_search @startIndex=?,@pageSize=?,@text=?,@idCategory=?,@status=?,@sort=?",
    "read": "SELECT T.[id], [date], [title], [note], [idCategory], [category], [completed], [created], [modified]"
    + " FROM [todos] T INNER JOIN [categories] C ON T.[idCategory]=C.[id]"
    + " WHERE T.[id]=?;",
    "insert": "INSERT INTO [todos] ([date],[title],[note],[idCategory],[created],[modified]) VALUES(?,?,?,?,GETDATE(),GETDATE());",
    "update": "UPDATE [todos] SET [date]=?,[title]=?,[note]=?,[idCategory]=?,[completed]=?,[modified]=GETDATE() WHERE [id]=?;",
    "remove": "DELETE FROM [todos] WHERE [id]=?;",
    "toggle": "UPDATE [todos] SET [completed]=CASE WHEN [completed] is null THEN GETDATE() ELSE null END, [modified]=GETDATE() WHERE [id]=?;",
    "updateCategory": "UPDATE [todos] SET [idCategory]=?,[modified]=GETDATE() WHERE [id]=?;",
    "updateCategoryRead": "SELECT [id],[idCategory] FROM [todos] WHERE [id]=?;",
    "categories": "SELECT [id],[category],[color] FROM [categories] ORDER BY [id];",
    "statistics": "SELECT c.[id],C.[category], C.[color], count(*) AS [count] FROM [todos] T"
    + " INNER JOIN [dbo].[categories] C ON T.[IDCategory]=C.[ID]"
    + " GROUP BY c.[ID],c.category, c.color"
    + " ORDER BY c.[ID];"
}

# definizione api


def todo_search():
    result = service_status_get([])
    try:
        id_category_s = request.args.get("idCategory")
        page_s = request.args.get("page")
        size_s = request.args.get("size")
        sort = request.args.get("sort")
        status_s = request.args.get("status")
        text = request.args.get("text")

        id_category = -1
        page_number = 0
        page_size = 10
        status = 0
        if id_category_s.isnumeric():
            id_category = int(id_category_s)
        if page_s.isnumeric():
            page_number = int(page_s)
        if size_s.isnumeric():
            page_size = int(size_s)
        if status_s.isnumeric():
            status = int(status_s)

        start_index = (page_number - 1) * page_size

        params = (start_index, page_size, text,
                  id_category, status, sort)

        with __db_get_connection() as cnn:
            with __db_get_cursor(cnn, queries["search"], params) as cursor:
                for row in cursor:
                    result["data"].append(__todo_get_data_item(row, False))
        count = len(result["data"])

        service_status_add_success(
            result, f"Readed startIndex: {start_index}, items:{count}")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def todo_get(id_s):
    result = service_status_get()
    try:
        id = 0
        if id_s.isnumeric():
            id = int(id_s)
        if id < 0:
            service_status_add_error(result, "Invalid id")
            return result

        count = __todo_get_item(result, id)

        service_status_add_success(result, f"Readed: {count}")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def __todo_get_item(result, id):
    params = (id)
    count = 0
    with __db_get_connection() as cnn:
        with __db_get_cursor(cnn, queries["read"], params) as cursor:
            row = cursor.fetchone()
            if row:
                count = 1
                result["data"] = __todo_get_data_item(row, True)
    return count


def __todo_get_data_item(row, detail=False):
    if detail:
        item = {
            "id": row[0],
            "date": row[1]+"T00:00:00.00Z",
            "title": row[2],
            "note": row[3],
            "idCategory": row[4],
            "category": row[5],
            "completed": row[6],
            "created": row[7].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "modified": row[8].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
    else:
        item = {
            "id": row[0],
            "date": row[1]+"T00:00:00.00Z",
            "title": row[2],
            "note": row[3],
            "idCategory": row[4],
            "category": row[5],
            "color": row[6],
            "completed": row[7],
            "created": row[8].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "modified": row[9].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "totalItems": row[10]
        }
    if item["completed"] != None:
        item["completed"] = item["completed"]+"T00:00:00.00Z"
    return item


def todo_insert():
    result = service_status_get()
    try:
        data = request.get_json()

        date_s = data.get("date")
        title = data.get("title")
        id_category = data.get('idCategory')
        note = data.get('note')

        # validazione
        if date_s == None:
            service_status_add_error(result, "`date` required")
        if title == None:
            service_status_add_error(result, "`title` required")
        if id_category == None or id_category < 0:
            service_status_add_error(result, "`idCategory` required")
        if len(result["messages"]) > 0:
            return result

        date = datetime.strptime(date_s, '%Y-%m-%dT%H:%M:%S.%fZ')

        params = (date, title, note, id_category)
        ___db_execute_cursor(queries["insert"], params)

        service_status_add_success(result, "Inserted")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def todo_update():
    result = service_status_get()
    try:
        data = request.get_json()

        id = data.get("id")
        date_s = data.get("date")
        title = data.get("title")
        id_category = data.get("idCategory")
        note = data.get("note")
        completed_s = data.get("completed")

        # validazione
        if id < 0:
            service_status_add_error(result, "Invalid id")
        if date_s == None:
            service_status_add_error(result, "`date` required")
        if title == None:
            service_status_add_error(result, "`title` required")
        if id_category == None or id_category < 0:
            service_status_add_error(result, "`idCategory` required")
        if len(result["messages"]) > 0:
            return result

        date = datetime.strptime(date_s, '%Y-%m-%dT%H:%M:%S.%fZ')
        completed = None
        if completed_s != None:
            completed = datetime.strptime(completed_s, '%Y-%m-%dT%H:%M:%S.%fZ')

        params = (date, title, note, id_category, completed, id)
        ___db_execute_cursor(queries["update"], params)

        service_status_add_success(result, f"Updated id: {id}")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def todo_delete():
    result = service_status_get()
    try:
        data = request.get_json()

        id = data.get("id")

        # validazione
        if id == None:
            service_status_add_error(result, "`id` required")
            return result

        params = (id)
        ___db_execute_cursor(queries["remove"], params)

        service_status_add_warnig(result, f"Deleted id: {id}")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def todo_toggle():
    result = service_status_get()
    try:
        data = request.get_json()

        id = data.get("id")

        # validazione
        if id == None:
            service_status_add_error(result, "`id` required")
            return result

        params = (id)
        ___db_execute_cursor(queries["toggle"], params)

        __todo_get_item(result, id)

        service_status_add_success(result, f"Toggled id: {id}")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def todo_update_category():
    result = service_status_get()
    try:
        data = request.get_json()

        id = data.get("id")
        id_category = data.get("idCategory")

        # validazione
        if id == None or id < 0:
            service_status_add_error(result, "Invalid id")
        if id_category == None or id_category < 0:
            service_status_add_error(result, "`idCategory` required")
        if len(result["messages"]) > 0:
            return result

        params = (id_category, id)
        ___db_execute_cursor(queries["updateCategory"], params)

        params = (id)
        with __db_get_connection() as cnn:
            with __db_get_cursor(cnn, queries["updateCategoryRead"], params) as cursor:
                row = cursor.fetchone()
                if row:
                    result["data"] = {
                        "id": row[0],
                        "idCategory": row[1]
                    }

        service_status_add_success(result, f"Updated  category id: {id}")
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def category_get_all():
    result = service_status_get([])
    try:
        with __db_get_connection() as cnn:
            with __db_get_cursor(cnn, queries["categories"]) as cursor:
                for row in cursor:
                    item = {
                        "id": row[0],
                        "category": row[1],
                        "color": row[2]
                    }
                    result["data"].append(item)
        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result


def statistics():
    result = service_status_get([])
    try:

        with __db_get_connection() as cnn:
            with __db_get_cursor(cnn, queries["statistics"]) as cursor:
                for row in cursor:
                    item = {
                        "id": row[0],
                        "category": row[1],
                        "color": row[2],
                        "count": row[3]
                    }
                    result["data"].append(item)

        result["success"] = True
    except Exception as ex:
        service_status_add_error(result, str(ex))
    return result
