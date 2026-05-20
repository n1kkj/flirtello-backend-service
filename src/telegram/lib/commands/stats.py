from sqlalchemy import text
from sqlmodel import Session


async def command(engine):
    with Session(engine) as session:
        with open("lib/commands/stats.sql") as f:
            result = session.execute(text(f.read()))
            result = result.all()
        return "\n".join([f"*{x[0]}*: {x[5]} ({int(x[1])}, {int(x[2])})" for x in result])
