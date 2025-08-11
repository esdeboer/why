import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib import request, parse
from time import gmtime, strftime
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

wikins = {'': 'http://www.mediawiki.org/xml/export-0.11/'}
uuidnamespace = UUID("0e9a6798-b290-45bf-a8a8-7483a53d0fab")
timezone = ZoneInfo("Europe/Amsterdam")
warnings = False
formatstring = '%Y-%m-%dT%H:%M:%S%:z'

def loadsessions():
    req = request.Request("https://wiki.why2025.org/Special:Export", data="title=Special%3AExport&catname=session&addcat=Add&pages=&curonly=1&wpDownload=1&wpEditToken=%2B%5C".encode())
    with request.urlopen(req) as response:
        xml = response.read().decode("utf-8")

    sessions = ""
    for line in xml.splitlines():
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
    with request.urlopen(req) as response:
        xml = response.read().decode("utf-8")
    return xml

def createfrabxml(xml):
    global warnings
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
    ET.SubElement(conference, "time_zone_name").text = timezone.key
    ET.SubElement(conference, "track").set("name","Self Organized Sessions")

    eventsbydateandroom = dict()
    for e in xml.findall("page", wikins):
        eventelement = ET.Element("event")
        title = e.find("title", wikins).text
        title = title.removeprefix('Session:')
        ET.SubElement(eventelement, "title").text = title
        ET.SubElement(eventelement, "track").text = "Self Organized Sessions"
        body = e.find("revision", wikins).find("text", wikins).text
        content = body.partition("}}")
        description = content[2].strip()
        session = content[0].removeprefix('{{Session').strip()

        extrainfo = ""

        # todo multiline things?
        for line in session.splitlines():
            if line.startswith("|Has description"):
                ET.SubElement(eventelement, "abstract").text = line.removeprefix("|Has description=")
            elif line.startswith("|Has session type"):
                ET.SubElement(eventelement, "type").text = line.removeprefix("|Has session type=")
            elif line.startswith("|Has website"):
                ET.SubElement(eventelement, "url").text = line.removeprefix("|Has website=")
            elif line.startswith("|Held in language"):
                ET.SubElement(eventelement, "language").text = line.removeprefix("|Held in language=")[0:2]
            elif line.startswith("|Is organized by"):
                persons = ET.SubElement(eventelement,"persons")
                ET.SubElement(persons, "person").text = line.removeprefix("|Is organized by=")
            elif line.startswith("|Has signup") and line.removeprefix("|Has signup=") == "Yes":
                extrainfo = "\nNeeds signup" + extrainfo
            elif line.startswith("|Is for kids") and line.removeprefix("|Is for kids=") == "Yes":
                extrainfo = "\nIs for kids" + extrainfo
            elif line.startswith("|Is for age range"):
                extrainfo = extrainfo + "\nAge range: " + line.removeprefix("|Is for age range=")
            elif line.startswith("|Has tags"):
                extrainfo = extrainfo + "\ntags:" + line.removeprefix("|Has tags=")
            elif line.startswith("|Has keywords"):
                extrainfo = extrainfo + "\nkeywords: " + line.removeprefix("|Has keywords=")

        events = []

        while description.startswith('{{Event'):
            descriptions = description.partition("}}")
            events.append(descriptions[0])
            description = descriptions[2].strip()

        extrainfo = extrainfo.strip()
        if extrainfo.isspace != "":
            description = extrainfo + "\n" + description
        description = description.strip()

        # add sessions without an event to midnight day after last day to show them to the user
        if len(events) == 0:
            event = eventelement.__copy__()
            starttime = "2025-08-13T00:00:00+02:00"
            ET.SubElement(event, "date").text = starttime
            ET.SubElement(event, "time").text = starttime[11:16]
            ET.SubElement(event, "duration").text = "01:00"
            event.set("guid", str(uuid5(uuidnamespace, title + "0")))
            description = "Generated time to make session visible, might need an actual date and time" + "\n" + description
            ET.SubElement(event, "description").text = description.strip()
            if validevent(event):
                eventsbydateandroom.setdefault(starttime[0:10], dict()).setdefault("undetermined",[]).append(event)

        ET.SubElement(eventelement, "description").text = description

        for i in range(len(events)):
            event = eventelement.__copy__()
            starttime = ""
            room = "undetermined"
            for line in events[i].splitlines():
                if line.startswith("|Has start time"):
                    starttime = line.removeprefix("|Has start time=")
                    try:
                        timewithzone = datetime.fromisoformat(starttime)
                    except ValueError as e:
                        warnings = True
                        print("Invalid event, has wrong formatted start time: " + title + " " + line)
                        starttime = "2025-08-13T00:00:00+02:00"
                        timewithzone = datetime.fromisoformat(starttime)
                    if timewithzone.tzinfo is None:
                        timewithzone = timewithzone.replace(tzinfo=timezone)
                    timewithzone.astimezone(timezone)
                    ET.SubElement(event, "date").text =  timewithzone.strftime(formatstring)
                    ET.SubElement(event, "start").text = timewithzone.strftime("%H:%M")
                elif line.startswith("|Has duration"):
                    try:
                        ET.SubElement(event, "duration").text = strftime("%H:%M", gmtime(
                            int(line.removeprefix("|Has duration=")) * 60))
                    except ValueError as e:
                        print("Invalid event, has wrong duration: " + title + " " + line)
                elif line.startswith("|Has session location"):
                    room = line.removeprefix("|Has session location=")
                elif line.startswith("|Has subtitle"):
                    ET.SubElement(event, "subtitle").text = line.removeprefix("|Has subtitle=")

            if event.find("duration") is None:
                ET.SubElement(event, "duration").text = "00:10"
                event.find("description").text = ("Missing duration, check with organiser, dummy 10 minutes added" + "\n" + description).strip()

            if event.find("date") is None:
                ET.SubElement(event, "date").text = "2025-08-13T00:00:00+02:00"
                event.find("description").text = ("Missing date, check with organiser, event put at last day" + "\n" + description).strip()

            guid = title + str(i)
            event.set("guid", str(uuid5(uuidnamespace, guid)))
            if validevent(event):
                if(starttime == ""):
                    starttime = "2025-08-13"
                eventsbydateandroom.setdefault(starttime[0:10], dict()).setdefault(room,[]).append(event)

    schedulejson = []

    for date in sorted(eventsbydateandroom.keys()):
        day = ET.SubElement(schedule, "day")
        day.set("date", date)
        for roomname in sorted(eventsbydateandroom[date].keys()):
            room = ET.SubElement(day, "room")
            room.set("name", roomname)
            room.set("guid", str(uuid5(uuidnamespace, roomname)))

            for event in eventsbydateandroom[date][roomname]:
                room.append(event)
                duration = event.find("duration").text
                url = event.find("url")
                type = event.find("type")
                # language = event.find("language")
                # speakers = event.find("persons")


                schedulejson.append({
                    "id": event.get("guid"),
                    "title": event.find("title").text,
                    "description": event.find("description").text,
                    # "date": event.find("date").text,
                    "start": event.find("date").text,
                    "end": (datetime.fromisoformat(event.find("date").text) +  timedelta(hours=int(duration[0:2])) + timedelta(minutes=int(duration[3:6]))).strftime(formatstring),
                    "room": roomname,
                    "url": url.text if url is not None else "",
                    "type": type.text if type is not None else "",
                    # "language": language.text if language is not None else "",
                    # "speakers": speakers.text if speakers is not None else "",
                    # "trackColor": "#B03BBF"
                })

        # Todo no date

    with open("public/sessions.json", 'w') as f:
        json.dump(schedulejson, f, indent=2)

    tree = ET.ElementTree(schedule)
    ET.indent(tree)
    return tree


def validevent(event):
    global warnings
    date = event.find("date")
    if (event.get("guid").isspace() or event.find("title").text.isspace()
            or date is None or event.find("duration") is None):
        print("Invalid event, some attributes are missing." + ET.tostring(event, encoding='unicode'))
        warnings = True
        return False
    if datetime.fromisoformat(date.text).tzinfo is None:
        print("Invalid event, date has no timezone" + ET.tostring(event, encoding='unicode'))
        warnings = True
        return False
    return True

def mergexml(schedule,sessions):
    conference = schedule.find("conference")
    title = conference.find("title")
    title.text = title.text + " with Self Organized Sessions"
    conference.append(sessions.find("conference").find("track"))

    daysinsessions = sessions.findall("day")
    daysinschedule = schedule.findall("day")

    for day in daysinsessions:
        date = day.get("date")
        dayinschedule = [x for x in daysinschedule if x.get("date") == date]

        if len(dayinschedule) == 1:
            dayinschedule[0].extend(day.findall("room"))
        else:
            schedule.append(day)

    tree = ET.ElementTree(schedule)
    ET.indent(tree,"    ")
    return tree


if __name__ == '__main__':
    # file = open("WHY2025+wiki.xml")
    # sessionsxml = ET.fromstring(file.read())
    # file.close()

    sessionsxml = loadsessions()
    sessionsxml = ET.fromstring(sessionsxml)

    result = createfrabxml(sessionsxml)
    result.write("public/sessions.xml","utf-8",True)

    # file = open("schedule.xml")
    # whyxml = ET.fromstring(file.read())
    # file.close()

    with request.urlopen("https://program.why2025.org/why2025/schedule/export/schedule.xml") as response:
        whyxml = ET.fromstring(response.read().decode("utf-8"))

    merged = mergexml(whyxml,result)
    merged.write("public/merged.xml","utf-8",True)

    # if warnings:
    #     sys.exit(137)

    # ET.dump(result)

    # print(result)
