from collections import defaultdict

UPDATE_INTERVAL = 30


class Targets:
    def __init__(self):
        self.targets = defaultdict(Target)

    def add_target(self, id, name, image, color, party):
        self.targets[id] = Target(
            id=id, name=name, image=image, color=color, party=party
        )

    def get_target(self, id):
        return self.targets[id]

    def get_targets(self):
        return self.targets.values()


class Target:
    def __init__(self, id, name, image, color, party):
        self.id = id
        self.name = name
        self.image = image
        self.color = color
        self.party = party


TARGETS = Targets()
TARGETS.add_target(
    id="pedro_sanchez",
    name="Pedro Sanchez",
    image="pedro_sanchez.jpg",
    color="#B12418",
    party="PSOE",
),
TARGETS.add_target(
    id="pablo_iglesias",
    name="Pablo Iglesias",
    image="pablo_iglesias.jpg",
    color="#984DAF",
    party="Podemos",
),
TARGETS.add_target(
    id="ines_arrimadas",
    name="Inés Arrimadas",
    image="ines_arrimadas.jpg",
    color="#EA7D3F",
    party="Ciudadanos",
),
TARGETS.add_target(
    id="pablo_casado",
    name="Pablo Casado",
    image="pablo_casado.jpg",
    color="#53B3E3",
    party="PP",
),
TARGETS.add_target(
    id="santiago_abascal",
    name="Santiago Abascal",
    image="santiago_abascal.jpg",
    color="#8EB148",
    party="VOX",
),
