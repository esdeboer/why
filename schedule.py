import xml.etree.ElementTree as ET
from urllib import request, parse
from time import gmtime, strftime
from uuid import UUID, uuid5

wikins = {'': 'http://www.mediawiki.org/xml/export-0.11/'}
uuidnamespace = UUID("0e9a6798-b290-45bf-a8a8-7483a53d0fab")

def loadsessions():
    req = request.Request("https://wiki.why2025.org/Special:Export", data="title=Special%3AExport&catname=session&addcat=Add&pages=&curonly=1&wpDownload=1&wpEditToken=%2B%5C".encode())
    resp = request.urlopen(req)
    t = resp.read().decode("utf-8")

    sessions = ""
    for line in t.splitlines():
        if line.startswith('Session:'):
            if line.find("</textarea>") != -1:
                sessions = sessions + "Session:FHB:_Kefir_Making"
            else :
                sessions = sessions + line + "\r\n"

    formdata = dict()
    formdata["title"] =	"Special:Export"
    formdata["catname"] = "session"
    formdata["pages"] = sessions
    formdata["curonly"] = "1"
    formdata["wpDownload"] = "1"
    formdata["wpEditToken"] = "+\\"

    data = parse.urlencode(formdata).encode()
    req = request.Request("https://wiki.why2025.org/Special:Export",data)
    resp = request.urlopen(req)
    return resp.read().decode("utf-8")

def createfrabxml(xml):
    schedule = ET.Element("schedule")
    conference = ET.SubElement(schedule, "conference")
    ET.SubElement(conference, "title").text = "WHY2025 Self Organized Sessions"
    ET.SubElement(conference, "acronym").text = "why2025"
    ET.SubElement(conference, "start").text = "2025-08-08"
    ET.SubElement(conference, "end").text = "2025-08-12"
    ET.SubElement(conference, "days").text = "5"
    ET.SubElement(conference, "base_url").text = "https://cfp.why2025.org"
    # <timeslot_duration>00:05</timeslot_duration>
    ET.SubElement(conference, "logo").text = "https://cfp.why2025.org/media/why2025/img/logo_yz1ryVf.png"
    ET.SubElement(conference, "time_zone_name").text = "Europe/Amsterdam"

    eventsbydateandroom = dict()
    for e in xml.findall("page", wikins):
        eventelement = ET.Element("event")
        title = e.find("title", wikins).text
        title = title.removeprefix('Session:')
        ET.SubElement(eventelement, "title").text = title
        ET.SubElement(eventelement, "track").text = "Self Organized Session"
        # print(title)
        body = e.find("revision", wikins).find("text", wikins).text
        content = body.partition("}}")
        description = content[2].strip()
        # print(content[0])
        session = content[0].removeprefix('{{Session').strip()

        # todo multiline things?
        for line in session.splitlines():
            if line.startswith("|Has description"):
                ET.SubElement(eventelement, "abstract").text = line.removeprefix("|Has description=")
            elif line.startswith("|Has session type"):
                ET.SubElement(eventelement, "type").text = line.removeprefix("|Has session type=")
            elif line.startswith("|Has website"):
                ET.SubElement(eventelement, "url").text = line.removeprefix("|Has website=")
            elif line.startswith("|Has language"):
                ET.SubElement(eventelement, "language").text = line.removeprefix("|Has language=")
            elif line.startswith("|Is organized by"):
                persons = ET.SubElement(eventelement,"persons")
                ET.SubElement(persons, "person").text = line.removeprefix("|Is organized by=")
            # print(line)

        # print(description)
        events = []

        while description.startswith('{{Event'):
            descriptions = description.partition("}}")
            # print(description[0])
            events.append(descriptions[0])
            # print(events)
            description = descriptions[2].strip()
            # print(description)

        ET.SubElement(eventelement, "description").text = description

        for e in events:
            event = eventelement.__copy__()
            time = ""
            room = "undetermined"
            for line in e.splitlines():
                if line.startswith("|Has start time"):
                    time = line.removeprefix("|Has start time=")
                    ET.SubElement(event, "date").text = time
                    ET.SubElement(event, "time").text = time[11:16]
                elif line.startswith("|Has duration"):
                    ET.SubElement(event, "duration").text = strftime("%H:%M", gmtime(
                        int(line.removeprefix("|Has duration=")) * 60))
                elif line.startswith("|Has session location"):
                    room = line.removeprefix("|Has session location=")

            guid = title
            if len(events) > 1:
                guid = title + time
            event.set("guid", str(uuid5(uuidnamespace, guid)))

            eventsbydateandroom.setdefault(time[0:10], dict()).setdefault(room,[]).append(event)

        for date in sorted(eventsbydateandroom.keys()):
            for roomname in sorted(eventsbydateandroom[date].keys()):
                day = ET.SubElement(schedule, "day")
                day.set("date", date)
                room = ET.SubElement(day, "room")
                room.set("name", roomname)
                room.set("guid", str(uuid5(uuidnamespace, roomname)))

                for event in eventsbydateandroom[date][roomname]:
                    room.append(event)

        # Todo no date

        # print(events)

    # print(xml.findall("page",wiki_namespace))
    tree = ET.ElementTree(schedule)

    ET.indent(tree)
    # ET.dump(schedule)

    return tree


if __name__ == '__main__':
    # file1 = open("WHY2025+wiki.xml")
    # sessionsxml = ET.fromstring(file1.read())
    # file1.close()

    sessionsxml = loadsessions()
    sessionsxml = ET.fromstring(sessionsxml)

    result = createfrabxml(sessionsxml)
    result.write("public/sessions_schedule.xml")

    # ET.dump(result)

    # print(result)
