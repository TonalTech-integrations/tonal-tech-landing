"""Promueve un usuario a administrador.

Uso:
    python -m backend.scripts.make_admin usuario@email.com
    python -m backend.scripts.make_admin usuario@email.com --revoke
"""

import argparse

from backend.services.persistence import get_user_by_email, set_admin


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestiona el flag is_admin de un usuario")
    parser.add_argument("email", help="Email del usuario")
    parser.add_argument("--revoke", action="store_true", help="Quitar permisos de admin")
    args = parser.parse_args()

    user = get_user_by_email(args.email)
    if not user:
        print(f"ERROR: usuario '{args.email}' no encontrado")
        raise SystemExit(1)

    set_admin(args.email, is_admin=not args.revoke)
    estado = "SIN permisos de admin" if args.revoke else "ADMIN"
    print(f"OK: {args.email} ahora es {estado}")


if __name__ == "__main__":
    main()
