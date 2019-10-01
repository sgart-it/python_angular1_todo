import os
from flask import Flask, render_template, request, send_from_directory
from flask_cors import CORS, cross_origin
from json import dumps
#from flask_jsonpify import jsonify
import services

# static files
static_file_dir = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'static')

app = Flask(__name__, static_url_path="", static_folder=static_file_dir)
CORS(app)

# percorso base
@app.route("/")
def main():
    return render_template("index.html", title="TODO python - sgart.it")


# route api
@app.route("/api/categories", methods=["GET"])
def category_get_all():
    return services.category_get_all()


@app.route("/api/todo/search", methods=["GET"])
def todo_search():
    return services.todo_search()


@app.route("/api/todo/<id>", methods=["GET"])
def todo_get(id):
    return services.todo_get(id)


@app.route("/api/todo/insert", methods=["POST"])
def todo_insert():
    return services.todo_insert()


@app.route("/api/todo/update", methods=["POST"])
def todo_update():
    return services.todo_update()


@app.route("/api/todo/delete", methods=["POST"])
def todo_delete():
    return services.todo_delete()

@app.route("/api/todo/category", methods=["POST"])
def todo_category():
    return services.todo_update_category()

@app.route("/api/todo/toggle", methods=["POST"])
def todo_toggle():
    return services.todo_toggle()

@app.route("/api/statistics", methods=["GET"])
def statistics():
    return services.statistics()

# verifica se è il programma principale
if __name__ == "__main__":
    app.run(debug=True, port=5000)
