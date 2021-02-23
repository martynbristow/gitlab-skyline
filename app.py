# -*- coding: utf-8 -*-
import os
from tornado.web import Application, RequestHandler
import tornado.ioloop

from gitlabskyline import gitlab_skyline


class WelcomeHandler(RequestHandler):
    def get(self):
        self.render("index.html", title="GitLab Skylines")

    def post(self):
        self.render("index.html", title="GitLab Skylines")


class SkylineHandler(RequestHandler):
    def get(self, username, year=2020):
        self.render("index.html")


def make_app():
    return Application([
        (r"/", WelcomeHandler),
        (r"/([a-zA-Z0-9]+)", SkylineHandler),
        (r"/([a-zA-Z0-9]+)/([0-9]+)", SkylineHandler)
    ],
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        template_path=os.path.join(os.path.dirname(__file__), "templates")
    )


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    try:  # localhost:8888
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        pass