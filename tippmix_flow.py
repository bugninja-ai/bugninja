import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

# to generate a random fake name

TIPPMIX_PROMPT = """
Két egyedi fogadás (foci és kosár) létrehozása és ellenőrzése a Tippmix oldalon.

**Elvárt működés:**
- A rendszer engedje, hogy a felhasználó létrehozzon két egyedi fogadást (egy focira, egy kosárra), 
ezek jelenjenek meg a szelvényen, és amikor a lottózóba kérjük a szelvényt, kapjunk egy érvényes, egyedi sorszámot.
""".strip()


async def tippmix_1() -> None:

    task = BugninjaTask(
        description=TIPPMIX_PROMPT,
        extra_instructions=[
            "Nyisd meg a Tippmix főoldalát: https://tippmix.hu",
            "Menj a 'Sportfogadás' részhez a felső menüből a 'Fogadás' gombbal",
            "----",
            "Szűrd az eseményeket úgy, hogy csak a 'Prematch' kategória látszódjon, majd az 'Összes sport' helyett válaszd a 'Futball'-t, és nyomd meg a listázás gombot.",
            "Válaszd ki az első focimeccset, majd használd a felső 'Fogadáskészítő' gombot a szűréshez",
            "Elérhető 3 kimenetelű (hazai [H], döntetlen [D], vendég [V]) és 2 kimenetelű (hazai [H], vendég [V]) fogadás, de csak a 3 kimenetelűt szabad választanod",
            "Ha nem látsz 3 kimenetelű fogadási lehetőséget, görgess lejjebb, amíg az első meg nem jelenik",
            "Ha látsz 3 kimenetelű lehetőséget, válaszd a hazai csapat [H] opcióját",
            "Más típusú fogadást nem választhatsz, erre figyelj oda!",
            "Ha az adott meccsnél nincs egyáltalán 3 kimenetelű lehetőség, menj vissza, és válaszd a következő eseményt",
            "Ismételd, amíg nem találsz egy ilyen fogadást",
            "----",
            "Váltsd át a sport szűrőt kosárlabdára, és ismételd meg a fenti folyamatot egy 3 kimenetelű fogadás kiválasztásához",
            "Ellenőrizd, hogy az általad összeválogatott fogadásokban pontosan a 2 egyedi fogadás szerepel, ehhez kattints a jobb felső sarokban a 'Szelvény' gombra",
            "Töltsd ki a felugró űrlapot 2000 Ft tét megadásával, válaszd az 'Egyszeres kötés' opciót, majd küldd el a szelvényt az elfogadás gombbal",
            "Jegyezd fel a weboldal által adott egyedi azonosítót/sorszámot, majd zárd be a böngészőt",
        ],
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(tippmix_1())
