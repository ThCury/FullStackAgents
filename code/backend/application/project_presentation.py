class ProjectPresentation:
    @staticmethod
    def list_item(project: dict) -> dict:
        return {
            "project_id": project["_id"],
            "name": project["name"],
            "status": project["status"],
            "last_run_id": project["context"].get("last_run_id"),
            "brasil_datetime": project["brasil_datetime"],
        }
