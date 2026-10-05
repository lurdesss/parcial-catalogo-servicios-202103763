def register_api(app):
    from . import auth, catalogs, imports, org, services
    for module in (auth, org, catalogs, services, imports):
        app.register_blueprint(module.bp)
