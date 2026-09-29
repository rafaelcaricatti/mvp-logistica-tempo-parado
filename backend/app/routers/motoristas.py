"""RF01 — Cadastro de motoristas/motoboys."""

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.core.security import apenas_gestao, qualquer_perfil
from app.schemas import MotoristaCreate, MotoristaOut, MotoristaUpdate, UsuarioOut
from app.services import auditoria

router = APIRouter(prefix="/motoristas", tags=["RF01 · Motoristas"])


@router.get("", response_model=list[MotoristaOut], summary="Lista motoristas")
def listar(
    apenas_ativos: bool = False, _: UsuarioOut = Depends(qualquer_perfil())
) -> list[MotoristaOut]:
    filtros = [("ativo", "==", True)] if apenas_ativos else None
    registros = repositories.motoristas().listar(filtros=filtros, ordenar_por="nome")
    return [MotoristaOut(**r) for r in registros]


@router.get("/{motorista_id}", response_model=MotoristaOut, summary="Detalha um motorista")
def obter(motorista_id: str, _: UsuarioOut = Depends(qualquer_perfil())) -> MotoristaOut:
    registro = repositories.motoristas().obter(motorista_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Motorista não encontrado.")
    return MotoristaOut(**registro)


@router.post(
    "",
    response_model=MotoristaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um motorista",
)
def criar(
    payload: MotoristaCreate, usuario: UsuarioOut = Depends(apenas_gestao())
) -> MotoristaOut:
    duplicado = repositories.motoristas().primeiro([("documento", "==", payload.documento)])
    if duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe motorista com o documento {payload.documento}.",
        )
    registro = repositories.motoristas().criar(payload.model_dump())
    auditoria.registrar("criar", "motorista", registro["id"], usuario, payload.model_dump())
    return MotoristaOut(**registro)


@router.put("/{motorista_id}", response_model=MotoristaOut, summary="Atualiza um motorista")
def atualizar(
    motorista_id: str,
    payload: MotoristaUpdate,
    usuario: UsuarioOut = Depends(apenas_gestao()),
) -> MotoristaOut:
    mudancas = payload.model_dump(exclude_unset=True, exclude_none=True)
    registro = repositories.motoristas().atualizar(motorista_id, mudancas)
    if registro is None:
        raise HTTPException(status_code=404, detail="Motorista não encontrado.")
    auditoria.registrar("atualizar", "motorista", motorista_id, usuario, {"mudancas": mudancas})
    return MotoristaOut(**registro)


@router.delete(
    "/{motorista_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove um motorista"
)
def remover(motorista_id: str, usuario: UsuarioOut = Depends(apenas_gestao())) -> None:
    if not repositories.motoristas().remover(motorista_id):
        raise HTTPException(status_code=404, detail="Motorista não encontrado.")
    auditoria.registrar("remover", "motorista", motorista_id, usuario)
