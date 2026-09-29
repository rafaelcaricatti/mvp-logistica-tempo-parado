"""RF02 — Cadastro de gerentes/coordenadores/donos de transportadora."""

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.core.security import apenas_gestao, qualquer_perfil
from app.schemas import GerenteCreate, GerenteOut, GerenteUpdate, UsuarioOut
from app.services import auditoria

router = APIRouter(prefix="/gerentes", tags=["RF02 · Gerentes"])


@router.get("", response_model=list[GerenteOut], summary="Lista gerentes")
def listar(_: UsuarioOut = Depends(qualquer_perfil())) -> list[GerenteOut]:
    return [GerenteOut(**r) for r in repositories.gerentes().listar(ordenar_por="nome")]


@router.get("/{gerente_id}", response_model=GerenteOut, summary="Detalha um gerente")
def obter(gerente_id: str, _: UsuarioOut = Depends(qualquer_perfil())) -> GerenteOut:
    registro = repositories.gerentes().obter(gerente_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Gerente não encontrado.")
    return GerenteOut(**registro)


@router.post(
    "", response_model=GerenteOut, status_code=status.HTTP_201_CREATED, summary="Cadastra gerente"
)
def criar(payload: GerenteCreate, usuario: UsuarioOut = Depends(apenas_gestao())) -> GerenteOut:
    registro = repositories.gerentes().criar(payload.model_dump(mode="json"))
    auditoria.registrar("criar", "gerente", registro["id"], usuario)
    return GerenteOut(**registro)


@router.put("/{gerente_id}", response_model=GerenteOut, summary="Atualiza um gerente")
def atualizar(
    gerente_id: str, payload: GerenteUpdate, usuario: UsuarioOut = Depends(apenas_gestao())
) -> GerenteOut:
    mudancas = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    registro = repositories.gerentes().atualizar(gerente_id, mudancas)
    if registro is None:
        raise HTTPException(status_code=404, detail="Gerente não encontrado.")
    auditoria.registrar("atualizar", "gerente", gerente_id, usuario, {"mudancas": mudancas})
    return GerenteOut(**registro)


@router.delete(
    "/{gerente_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove um gerente"
)
def remover(gerente_id: str, usuario: UsuarioOut = Depends(apenas_gestao())) -> None:
    if not repositories.gerentes().remover(gerente_id):
        raise HTTPException(status_code=404, detail="Gerente não encontrado.")
    auditoria.registrar("remover", "gerente", gerente_id, usuario)
