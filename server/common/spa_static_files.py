from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exception:
            if exception.status_code == 404:
                filename = path.split("/")[-1]
                if "." not in filename:
                    return await super().get_response("index.html", scope)
            raise exception
