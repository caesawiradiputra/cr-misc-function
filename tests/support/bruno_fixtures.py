"""Fixture FastAPI apps and hostile files, kept as text and written at test time.

Nothing here is a live module: `ruff`, `mypy` and the format hook run on the whole
repo, `fastapi` is not a dependency, and secret-shaped strings can trip push
protection. Fake secrets are built by concatenation.
"""

from __future__ import annotations

from pathlib import Path

APP_FILES: dict[str, str] = {
    "app/__init__.py": "",
    "app/main.py": """\
from fastapi import FastAPI

from app.api import legacy
from app.api.router import api_router

app = FastAPI(title="Orders")
app.include_router(api_router, prefix="/api/v1")
app.include_router(legacy.router)


@app.get("/health", tags=["ops"])
def health():
    return {"ok": True}
""",
    "app/api/__init__.py": "",
    "app/api/router.py": """\
from fastapi import APIRouter

from app.api.endpoints import orders

api_router = APIRouter()
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
""",
    "app/api/endpoints/__init__.py": "",
    "app/api/endpoints/orders.py": '''\
from fastapi import APIRouter

router = APIRouter()


@router.get("/{order_id}", tags=["detail"])
def get_order(order_id: int):
    """Get one order."""
    return {}


@router.post("/")
def create_order():
    return {}


def export_orders():
    return []


router.add_api_route("/export", export_orders, methods=["GET", "POST"])

for _path in ("/a", "/b"):
    router.add_api_route(_path, export_orders)
''',
    "app/api/legacy.py": """\
from fastapi import APIRouter

router = APIRouter(prefix="/old")


@router.delete("/{thing_id}")
async def remove(thing_id: str):
    return {}
""",
    "app/unused.py": """\
from fastapi import APIRouter

orphan = APIRouter()


@orphan.get("/never-mounted")
def never():
    return {}
""",
}

RELATIVE_APP_FILES: dict[str, str] = {
    "pkg/__init__.py": "",
    "pkg/main.py": """\
from fastapi import FastAPI

from .routes import router as shop_router

app = FastAPI()
app.include_router(shop_router, prefix="/shop")
""",
    "pkg/routes/__init__.py": "from .items import router\n",
    "pkg/routes/items.py": """\
from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])


@router.get("")
def list_items():
    return []
""",
}


PARAMS_APP_FILES: dict[str, str] = {
    "shop/__init__.py": "",
    "shop/models.py": """\
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Address(BaseModel):
    city: str = Field(..., min_length=1, max_length=20)
    zip_code: Optional[str] = None


class Customer(BaseModel):
    name: str = Field(..., max_length=30, example="Ann")
    age: int = Field(18, ge=0, le=120)
    nickname: Optional[str] = None
    address: Address
    previous: List[Address] = []

    class Config:
        schema_extra = {"example": {"name": "Ann", "age": 30}}


class CustomerV2(BaseModel):
    name: str = Field(min_length=1, examples=["Bob"])
    model_config = ConfigDict(json_schema_extra={"example": {"name": "Bob"}})


class Node(BaseModel):
    value: int
    child: Optional["Node"] = None


class L4(BaseModel):
    v: int


class L3(BaseModel):
    l4: L4


class L2(BaseModel):
    l3: L3


class L1(BaseModel):
    l2: L2
""",
    "shop/main.py": """\
from enum import Enum
from typing import Annotated, List, Literal, Optional

from fastapi import Body, Depends, FastAPI, Header, Path, Query, Request
from pydantic import conint

from shop import settings
from shop.models import Customer, CustomerV2, L1, Node

app = FastAPI()


class Color(str, Enum):
    red = "red"
    blue = "blue"


def get_db():
    return None


@app.get("/items/{item_id}")
def read_item(
    request: Request,
    item_id: int = Path(..., ge=1, le=999, example=42),
    q: str = Query(..., min_length=2, max_length=10, pattern="^[a-z]+$"),
    limit: int = Query(10, gt=0, lt=100, multiple_of=5),
    tag: Optional[str] = Query(None, min_length=1),
    tags: List[str] = Query(default=[], max_length=5),
    color: Color = Query(Color.red),
    mode: Literal["fast", "slow"] = "fast",
    x_token: str = Header(None),
    z: str = Query(..., max_length=settings.MAX),
    n: Annotated[int, Query(ge=1)] = 1,
    size: conint(ge=1, le=10) = 5,
    maybe: Optional[int] = None,
    db=Depends(get_db),
):
    return {}


@app.post("/customers")
def create(c: Customer):
    return {}


@app.post("/v2")
def create_v2(c: CustomerV2):
    return {}


@app.post("/bulk")
def bulk(items: List[Customer]):
    return {}


@app.post("/nodes")
def nodes(node: Node):
    return {}


@app.post("/deep")
def deep(body: L1):
    return {}


@app.get("/files/{file_path:path}")
def files(file_path: str):
    return {}


@app.put("/scalar-body")
def scalar_body(note: str = Body(..., embed=True, max_length=50)):
    return {}
""",
}


_TOKEN_MODEL = """\
class Token(BaseModel):
    access_token: str
    token_type: str
"""

AUTH_VARIANTS: dict[str, dict[str, str]] = {
    "oauth": {
        "svc/main.py": """\
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

app = FastAPI()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


"""
        + _TOKEN_MODEL
        + """

@app.post("/api/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()):
    return {}


@app.get("/me")
def me(tok: str = Depends(oauth2)):
    return {}
""",
    },
    "form_token": {
        "svc/main.py": """\
from fastapi import FastAPI, Form
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

app = FastAPI()
oauth2 = OAuth2PasswordBearer(tokenUrl="token")


class Out(BaseModel):
    jwt_token: str


@app.post("/token", response_model=Out)
def issue(client_id: str = Form(...), client_secret: str = Form(...)):
    return {}
""",
    },
    "default_field": {
        "svc/main.py": """\
from fastapi import FastAPI, Form
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2 = OAuth2PasswordBearer(tokenUrl="/login")


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    return {}
""",
    },
    "missing_route": {
        "svc/main.py": """\
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2 = OAuth2PasswordBearer(tokenUrl="/missing")


@app.get("/ping")
def ping():
    return {}
""",
    },
    "apikey_header": {
        "svc/main.py": """\
from fastapi import FastAPI
from fastapi.security import APIKeyHeader

app = FastAPI()
api_key = APIKeyHeader(name="X-API-Key")


@app.get("/ping")
def ping():
    return {}
""",
    },
    "apikey_query": {
        "svc/main.py": """\
from fastapi import FastAPI
from fastapi.security import APIKeyQuery

app = FastAPI()
api_key = APIKeyQuery(name="key")


@app.get("/ping")
def ping():
    return {}
""",
    },
    "bearer": {
        "svc/main.py": """\
from fastapi import FastAPI
from fastapi.security import HTTPBearer

app = FastAPI()
scheme = HTTPBearer()


@app.get("/ping")
def ping():
    return {}
""",
    },
    "basic": {
        "svc/main.py": """\
from fastapi import FastAPI
from fastapi.security import HTTPBasic

app = FastAPI()
scheme = HTTPBasic()


@app.get("/ping")
def ping():
    return {}
""",
    },
    "middleware": {
        "svc/main.py": """\
from fastapi import FastAPI

from svc.guard import Guard

app = FastAPI()
app.add_middleware(Guard)


@app.get("/ping")
def ping():
    return {}
""",
        "svc/__init__.py": "",
        "svc/guard.py": """\
from starlette.middleware.base import BaseHTTPMiddleware

API_KEY = "configured"


class Guard(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        supplied = request.headers.get("apikey")
        agent = request.headers["user-agent"]
        if not supplied or supplied != API_KEY:
            return None
        return await call_next(request)
""",
    },
    "none": {
        "svc/main.py": """\
from fastapi import FastAPI

app = FastAPI()


@app.get("/ping")
def ping():
    return {}
""",
    },
}


def write_files(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)


def write_app(root: Path) -> None:
    write_files(root, APP_FILES)


def write_hostile(root: Path, outside: Path) -> None:
    """Add a syntax-error module, ignored folders and symlinks that leave `root`."""
    write_files(
        root,
        {
            "app/broken.py": "def broken(:\n    pass\n",
            ".venv/lib/vendored.py": (
                "from fastapi import APIRouter\n"
                "r = APIRouter()\n\n@r.get('/vendored')\ndef v():\n    return 1\n"
            ),
            "legacy/old.py": (
                "from fastapi import APIRouter\n"
                "r = APIRouter()\n\n@r.get('/legacy')\ndef v():\n    return 1\n"
            ),
        },
    )
    outside.mkdir(parents=True, exist_ok=True)
    (outside / "secret_route.py").write_text(
        "from fastapi import APIRouter\n"
        "r = APIRouter()\n\n@r.get('/outside')\ndef o():\n    return 1\n",
        encoding="utf-8",
    )
    (root / "linked_file.py").symlink_to(outside / "secret_route.py")
    (root / "linked_dir").symlink_to(outside, target_is_directory=True)
