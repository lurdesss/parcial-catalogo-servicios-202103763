def register_api(app):
    from . import auth, catalogs, cmdb, dashboard, imports, org, processes, queues, services, tickets
    for module in (auth, org, catalogs, services, imports, cmdb, queues, processes, tickets, dashboard):
        app.register_blueprint(module.bp)
