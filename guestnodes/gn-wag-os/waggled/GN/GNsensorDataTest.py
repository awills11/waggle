#!/usr/bin/env python

""" This is a test of the communication and data cache architecture. It will use all default values for header. """ 
import sys
sys.path.append('../../../../devtools/protocol_common/')
from utilities import packetmaker
from send import send

data = 'AA0C2086654321182F14924C82CCE832558C45B383D198545822D562756B7888A3928CE2A18DCF88230D1926D61A6CCC28499829CB4B49EAAC2C269C5D8230C4E82AE5F824D3910277E811A285FED81F35DB62C35A042E126EDE1B4259961D08881CBBAAAC0CD55EABC4B26122B5521382DD5F14823DCE15827261162E78178217E18262719825E471A8258291B25BA21C8262461D49C2CC71A1E3B312641F86CBA987FE84FFDFFFFF2955'

packet = packetmaker.make_data_packet(data)
for pack in packet:
        send(pack)

