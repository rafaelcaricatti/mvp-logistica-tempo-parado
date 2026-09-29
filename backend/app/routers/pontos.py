"""RF03 — Cadastro de pontos (endereço e coordenadas)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.core.security import apenas_gestao, qualquer_perfil
from app.schemas import PontoCreate, PontoOut, PontoUpdate, UsuarioOut
from app.services import auditoria

router = APIRouter(prefix="/pontos", tags=["RF03 · Pontos"])


@router.get("", response_model=list[PontoOut], summary="Lista pontos cadastrados")
def listar(busca: str | None = None, _: UsuarioOut = Depends(qualquer_perfil())) -> list[PontoOut]:
    registros = repositories.pontos().listar(ordenar_por="endereco")
    if busca:
        termo = busca.lower()
        registros = [
            r
            for r in registros
            if termo in r.get("endereco", "").lower()
            or termo in (r.get("apelido") or "").lower()
        ]
    return [PontoOut(**r) for r in registros]


@router.get("/{ponto_id}", response_model=PontoOut, summary="Detalha um ponto")
def obter(ponto_id: str, _: UsuarioOut = Depends(qualquer_perfil())) -> PontoOut:
    registro = repositories.pontos().obter(ponto_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Ponto não encontrado.")
    return PontoOut(**registro)


@router.post(
    "", response_model=PontoOut, status_code=status.HTTP_201_CREATED, summary="Cadastra um ponto"
)
def criar(payload: PontoCreate, usuario: UsuarioOut = Depends(apenas_gestao())) -> PontoOut:
    registro = repositories.pontos().criar(payload.model_dump())
    auditoria.registrar("criar", "ponto", registro["id"], usuario, payload.model_dump())
    return PontoOut(**registro)


@router.put("/{ponto_id}", response_model=PontoOut, summary="Atualiza um ponto")
def atualizar(
    ponto_id: str, payload: PontoUpdate, usuario: UsuarioOut = Depends(apenas_gestao())
) -> PontoOut:
    mudancas = payload.model_dump(exclude_unset=True, exclude_none=True)
    registro = repositories.pontos().atualizar(ponto_id, mudancas)
    if registro is None:
        raise HTTPException(status_code=404, detail="Ponto não encontrado.")
    # RNF05 — alterações em pontos ficam auditadas.
    auditoria.registrar("atualizar", "ponto", ponto_id, usuario, {"mudancas": mudancas})
    return PontoOut(**registro)


@router.delete("/{ponto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove um ponto")
def remover(ponto_id: str, usuario: UsuarioOut = Depends(apenas_gestao())) -> None:
    if not repositories.pontos().remover(ponto_id):
        raise HTTPException(status_code=404, detail="Ponto não encontrado.")
    auditoria.registrar("remover", "ponto", ponto_id, usuario)
