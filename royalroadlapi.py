import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from shutil import rmtree
from tornado import (
    ioloop,
    httpclient,
)
from tornado.httpclient import (
    HTTPResponse,
)
from tornado.concurrent import (
    Future,
)
from typing import Optional, Tuple, List, cast, Dict
import base64
import os
import re
import time
import uuid
import zipfile

import sys, asyncio

if (
    sys.version_info[0] == 3
    and sys.version_info[1] >= 8
    and sys.platform.startswith("win")
):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

i = 0  # to track the ioloop
chapters_downloaded = []
chapters_html = {}
fiction_html = ""
directory = "Error/"
epub_index_start = 1
file_name_chapter_range = ""


def get_fiction(fiction_id: int, directory: str, start_chapter: int, end_chapter: int):
    global epub_index_start, file_name_chapter_range, final_location, plural

    my_fic = fic(fiction_id)

    # clarify and validate the chapter range
    start_chapter, end_chapter, epub_index_start = get_chapter_range(
        start_chapter, end_chapter
    )
    chapter_links_approved = my_fic.chapter_links[start_chapter:end_chapter]
    if chapter_links_approved != []:
        downloading_chapter_amount = len(chapter_links_approved)
        chapter_amount = len(my_fic.chapter_links)
        (
            start_chapter,
            end_chapter,
            epub_index_start,
            chapter_amount,
            downloading_chapter_amount,
            file_name_chapter_range,
            plural,
        ) = chapter_range_string_expressions(
            start_chapter,
            end_chapter,
            epub_index_start,
            chapter_amount,
            downloading_chapter_amount,
        )
        if file_name_chapter_range != "":
            downloading_chapter_str = (
                "chapter"
                + plural
                + file_name_chapter_range
                + ", "
                + str(downloading_chapter_amount)
                + "/"
                + str(chapter_amount)
            )
        elif chapter_amount != 1:
            downloading_chapter_str = (
                "chapter"
                + plural
                + " "
                + "1-"
                + str(chapter_amount)
                + ", "
                + str(downloading_chapter_amount)
                + "/"
                + str(chapter_amount)
            )
        else:
            downloading_chapter_str = (
                "chapter"
                + plural
                + " "
                + "1, "
                + str(downloading_chapter_amount)
                + "/"
                + str(chapter_amount)
            )  # only show one chapter in the download string
        print(
            f"Downloading ID {fiction_id} ({downloading_chapter_str}) ID {fiction_id}: {my_fic.title} - {my_fic.author} {file_name_chapter_range}.epub"
        )
        asyncio.run(get_chapters(chapter_links_approved, directory))
        return final_location
    else:
        if chapter_links == []:
            print("Downloading ID {}: Fiction contains no chapters.".format(fiction_id))
        else:
            print(
                "Downloading ID {}: Fiction contains no chapters in the given range".format(
                    fiction_id
                ),
                str(epub_index_start) + "-" + str(end_chapter) + ".",
            )  # alert the user that the fiction has no chapters in that range


def get_fictions(
    fiction_id_start=1, fiction_id_end=None, directory="Fictions/"
):  # downloads multiple fictions, defaulting to download all
    try:  # confirm the range is valid
        if fiction_id_end == None:
            fiction_id_end = (
                find_latest_fiction_id()
            )  # returns the most recent fictions id to download all fictions
        fiction_id_start = int(fiction_id_start)  # to confirm int validity
        fiction_id_end = int(fiction_id_end)  # to confirm int validity
        total = (
            fiction_id_end - fiction_id_start
        ) + 1  # the amount of fictions to download
        if fiction_id_end < fiction_id_start:  # you can't download backwards
            raise Exception(
                "Invalid Range."
            )  # raise a custom error about an invalid range as the range given is out of order (backwards) or invalid(mistyped)
    except:
        print(
            "Please use valid numbers!"
        )  # the numbers are actually letters, words, symboles or floats, etc.
    else:
        for i in range(fiction_id_start, fiction_id_end + 1):  # begin downloading queue
            try:  # attempt download
                get_fiction(i, directory)  # download fiction
                print(
                    "Progress:",
                    str(round((((i - (fiction_id_start)) + 1) / total) * 100, 2)) + "%",
                )  # print progress
                print(
                    "Remaining:", str((total - 1) - (i - (fiction_id_start)))
                )  # print remaining
            except:  # the download failed for some reason, often it doesn't exist
                print(
                    "Fiction {} Not Available.".format(i)
                )  # the fiction download failed
                print(
                    "Progress:",
                    str(round((((i - (fiction_id_start)) + 1) / total) * 100, 2)) + "%",
                )  # print progress
                print(
                    "Remaining:", str((total - 1) - (i - (fiction_id_start)))
                )  # print remaining
    finally:
        print("Program Complete.")  # the multidownload has failed or completed


def get_fictions_from_list(
    fiction_ids=None, directory="Fictions/"
):  # downloads multiple fictions, defaulting to download all
    try:  # confirm the range is valid
        total = len(fiction_ids)  # the amount of fictions to download
        if fiction_ids == None:  # you can't download nothing
            raise Exception("No Fictions.")  # raise a custom error about no fictions
    except:
        print(
            "Please include fiction ids!"
        )  # the numbers are actually letters, words, symboles or floats, etc.
    else:
        i = 0
        for fiction_id in fiction_ids:  # begin downloading queue
            try:  # attempt download
                get_fiction(fiction_id, directory)  # download fiction
            except:  # the download failed for some reason, often it doesn't exist
                print(
                    "Fiction {} Not Available.".format(fiction_id)
                )  # the fiction download failed
            finally:
                i += 1
                print(
                    "Progress:", str(round(((i) / total) * 100, 2)) + "%"
                )  # print progress
                print("Remaining:", str((total) - i))  # print remaining

    finally:
        print("Program Complete.")  # the multidownload has failed or completed


def get_user_data(user_id):  # returns general user data
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id)
        soup = request_soup(url)
        favorite_fictions = soup.findAll("span", attrs={"class": "stat-value"})[
            1
        ].text.strip()
        ratings = soup.findAll("span", attrs={"class": "stat-value"})[2].text.strip()
        data = soup.find("tbody").findAll("td")
        join_date = [data[0].text.strip(), data[0].find("time").get("unixtime").strip()]
        last_active = [
            data[1].text.strip(),
            data[1].find("time").get("unixtime").strip(),
        ]
        gender = data[2].text.strip()
        location = data[3].text.strip()
        bio = data[4].text.strip()
        data2 = soup.findAll("tbody")[1].findAll("td")
        fiction_amount = data2[0].text.strip().replace(",", "")
        total_words = data2[1].text.strip().replace(",", "")
        total_reviews_recieved = data2[2].text.strip().replace(",", "")
        followers = data2[3].text.strip().replace(",", "")
        favorites_recieved = data2[4].text.strip().replace(",", "")
        data = [
            join_date,
            last_active,
            gender,
            location,
            bio,
            fiction_amount,
            total_words,
            total_reviews_recieved,
            followers,
            favorites_recieved,
            ratings,
            favorite_fictions,
        ]
        return data
    except:
        print("Invalid User ID/Name Input (or profile).")


def get_user_achievements(user_id):  # returns user achievements
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id) + "/achievements"
        soup = request_soup(url)
        achievements = []
        achievement_listings = soup.find(
            "div", attrs={"class": "portlet-body achievements"}
        ).findAll("div", attrs={"class": "well achievement-well"})
        for achievement_listing in achievement_listings:
            title = (
                achievement_listing.text.strip()
                .split("\n")[0]
                .strip()
                .split(" (")[0]
                .strip("")
            )
            try:
                level_rn = (
                    achievement_listing.text.strip()
                    .split("\n")[0]
                    .strip()
                    .split(" (")[-1]
                    .strip(")")
                )
                level = rn_to_int(level_rn)
            except:
                level = 1
            description = achievement_listing.text.split("\n")[2].strip()
            achievements.append([title, level, description])
        return achievements
    except:
        print("Invalid User ID/Name Input (or profile).")


def rn_to_int(rn):  # resolve the roman numberals in achievement titles to integers
    try:
        symbols = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        num = 0
        pos = 0
        len_rn = len(rn)
        for character in rn:
            if pos != len_rn - 1:
                print(symbols[character], symbols[rn[pos + 1]])
                if symbols[character] > symbols[rn[pos + 1]]:
                    num += symbols[character]
                elif symbols[character] == symbols[rn[pos + 1]]:
                    num += symbols[character]
                else:
                    num -= symbols[character]
            else:
                num += symbols[character]
            pos += 1
    except:
        num = 1
    return num


# move below functions into external file


def get_user_fictions(user_id):  # returns user fictions
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id) + "/fictions"
        fictions = get_fictions_from_url(url)
        return fictions
    except:
        print("Invalid User ID/Name Input (or profile).")


def get_user_favorites(user_id):  # returns user favorites
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id) + "/favorites"
        favorites = get_fictions_from_url(url)
        return favorites
    except:
        print("Invalid User ID/Name Input (or profile).")


def get_fictions_from_url(url):
    soup = request_soup(url)
    try:
        pages = int(
            soup.find("ul", attrs={"class": "pagination"})
            .findAll("a")[-1]
            .get("href")
            .split("=")[-1]
        )
    except:
        pages = 1
    fictions = []
    fictions = extract_fictions_from_url(soup, fictions)
    if pages > 1:
        for i in range(2, pages + 1):
            url_page = str(url) + "?page=" + str(i)
            print(url_page)
            soup = request_soup(url_page)
            fictions = extract_fictions_from_url(soup, fictions)
    return fictions


def extract_fictions_from_url(soup, fictions):
    fiction_listings = soup.findAll(
        "div", attrs={"class": "col-xs-12 col-sm-6 col-md-4 col-lg-3 padding-bottom-10"}
    )
    for fiction_listing in fiction_listings:
        data = fiction_listing.find("div", attrs={"class": "mt-overlay-3"}).find(
            "div", attrs={"class": "mt-overlay"}
        )
        title = data.find("h2").text.strip().split("\n")[0]
        data2 = data.find("div", attrs={"class": "mt-info"})
        description = data2.find(
            "div", attrs={"class": "fiction-description"}
        ).text.strip()
        fiction_id = data2.findAll("a")[-1].get("href").split("/")[-2].strip()
        fictions.append([fiction_id, title, description])
    return fictions


def get_user_posts(user_id):  # returns all user posts
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id) + "/posts"
        soup = request_soup(url)
        try:
            pages = int(
                soup.find("ul", attrs={"class": "pagination"})
                .findAll("a")[-1]
                .get("href")
                .split("=")[-1]
            )
        except:
            pages = 1
        posts = []
        posts = get_user_posts_data(soup, posts)
        if pages > 1:
            for i in range(2, pages + 1):
                url_page = str(url) + "?page=" + str(i)
                print(url_page)
                soup = request_soup(url_page)
                posts = get_user_posts_data(soup, posts)
        return posts
    except:
        print("Invalid User ID/Name Input (or profile).")


def get_user_posts_data(soup, posts):
    post_listings = soup.find("li", attrs={"class": "forum-bg"}).findAll("li")
    for post_div in post_listings:
        post_content = post_div.find("div", attrs={"class": "topic-description-inner"})
        time_data = (
            post_div.find("div", attrs={"class": "topic-stats"})
            .find("small")
            .find("time")
        )
        last_post_data = post_div.find("div", attrs={"class": "topic-recent"})
        last_post_time_data = post_div.find(
            "div", attrs={"class": "topic-recent"}
        ).find("time")

        link = post_content.find("h4").find("a").get("href").strip()
        id_str = link.split("/")[-1]

        thread_id = id_str.split("?")[0]
        post_id = id_str.split("pid")[-1]
        title = post_content.find("h4").text.strip()
        content = post_content.find("p").text.strip()
        time = [time_data.text.strip(), time_data.get("unixtime").strip()]

        last_post_user_id = last_post_data.find("a").get("href").split("/")[-1].strip()
        last_post_user_name = last_post_data.find("a").text.strip()

        last_post_time = [
            last_post_time_data.text.strip(),
            last_post_time_data.get("unixtime").strip(),
        ]

        last_post = [last_post_user_id, last_post_user_name, last_post_time]

        posts.append([thread_id, post_id, link, title, content, time, last_post])
    return posts


def get_user_reviews(user_id):  # returns all user reviews
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id) + "/reviews"
        soup = request_soup(url)
        try:
            pages = int(
                soup.find("ul", attrs={"class": "pagination"})
                .findAll("a")[-1]
                .get("href")
                .split("=")[-1]
            )
        except:
            pages = 1
        print(pages)
        reviews = []
        reviews = get_user_reviews_data(soup, reviews)
        if pages > 1:
            for i in range(2, pages + 1):
                url_page = str(url) + "?page=" + str(i)
                print(url_page)
                soup = request_soup(url_page)
                reviews = get_user_reviews_data(soup, reviews)
        return reviews
    except:
        print("Invalid User ID/Name Input (or profile).")


def get_user_reviews_data(soup, reviews):
    review_listings = soup.find("div", attrs={"class": "portlet-body"})
    review_listings_bodys = review_listings.findAll(
        "div", attrs={"class": "row review"}
    )
    review_listings_ratings = review_listings.findAll(
        "div", attrs={"class": "row hidden-xs visible-sm visible-md visible-lg"}
    )
    counter = 0
    for review_div in review_listings_bodys:
        review_title = review_div.find(
            "h4", attrs={"class": "bold uppercase font-blue-dark"}
        ).text
        review_content = review_div.find("div", attrs={"class": "review-content"}).text
        links = review_div.findAll("a")
        fiction_title = links[0].text
        fiction_id = links[0].get("href").split("/")[-2]
        review_id = links[1].get("href").split("-")[-1]
        time = [links[1].text.strip(), links[1].find("time").get("unixtime").strip()]
        ratings = []
        rating_list = review_listings_ratings[counter].findAll(
            "ul", attrs={"class": "list-unstyled"}
        )  # int(review_listings_ratings[counter].find("ul", attrs={"class":"list-unstyled"}).find("div").get("class")[-1].split("-")[-1])/10 #out of five
        for item in rating_list:
            value = int(item.find("div").get("class")[-1].split("-")[-1]) / 10
            rating_type = item.find("li").text.split()[0].lower()
            ratings.append([rating_type, value])
        reviews.append(
            [
                review_title,
                review_content,
                fiction_title,
                fiction_id,
                review_id,
                time,
                ratings,
            ]
        )
        counter += 1
    return reviews


def get_user_threads(user_id):  # returns threads made by the user
    user_id = get_user_id(user_id)
    try:
        url = "https://www.royalroad.com/profile/" + str(user_id) + "/threads"
        soup = request_soup(url)
        try:
            pages = int(
                soup.find("ul", attrs={"class": "pagination"})
                .findAll("a")[-1]
                .get("href")
                .split("=")[-1]
            )
        except:
            pages = 1
        print(pages)
        threads = []
        threads = get_user_threads_data(soup, threads)
        if pages > 1:
            for i in range(2, pages + 1):
                url_page = str(url) + "?page=" + str(i)
                print(url_page)
                soup = request_soup(url_page)
                threads = get_user_threads_data(soup, threads)
        return threads
    except:
        print("Invalid User ID/Name Input (or profile).")


def get_user_threads_data(soup, threads):
    thread_listings = soup.find("li", attrs={"class": "forum-bg"}).findAll(
        "li", attrs={"class": "sticky"}
    )
    for thread_div in thread_listings:
        thread_content = thread_div.find(
            "div", attrs={"class": "topic-description-inner"}
        )
        time_data = thread_div.find(
            "div", attrs={"class": "topic-description-inner"}
        ).find("time")
        last_post_data = thread_div.find("div", attrs={"class": "topic-recent"})
        last_post_time_data = thread_div.find(
            "div", attrs={"class": "topic-recent"}
        ).find("time")
        link = thread_content.find("h4").find("a").get("href").strip()
        thread_id = link.split("/")[-1]
        title = thread_content.find("h4").text.strip()
        replies = (
            thread_div.find("span", attrs={"class": "topic-replies"})
            .text.strip()
            .split()[0]
            .replace(",", "")
        )
        views = (
            thread_div.find("span", attrs={"class": "topic-views"})
            .text.strip()
            .split()[0]
            .replace(",", "")
        )
        time = [time_data.text.strip(), time_data.get("unixtime").strip()]
        last_post_user_id = last_post_data.find("a").get("href").split("/")[-1].strip()
        last_post_user_name = last_post_data.find("a").text.strip()

        last_post_time = [
            last_post_time_data.text.strip(),
            last_post_time_data.get("unixtime").strip(),
        ]

        last_post = [last_post_user_id, last_post_user_name, last_post_time]

        threads.append([thread_id, link, title, replies, views, time, last_post])
    return threads


def get_user_id(user_name):  # returns a user's id
    try:
        int(user_name)  # check if the input value is a user_id and not a user_name
        user_id = user_name  # it was a user_id
    except:  # it was probably a user_name
        search_term = user_name.replace(" ", "+")  # replace spaces with plus signs
        url = "https://www.royalroad.com/user/memberlist?q=" + str(
            search_term
        )  # construct the url
        print(url)  # print the search url for debug or console purposes
        soup = request_soup(url)
        try:
            user_id = int(
                soup.find("tbody")
                .find("tr")
                .find("td")
                .find("a")
                .get("href")
                .split("/")[2]
            )  # attempt to gather the first user id
        except:  # there was no user with that id or the html is incorrect
            return None  # return none
    return user_id  # return the user id


def find_latest_fiction_id():  # find the latest fictiond id
    url = "https://www.royalroad.com/fictions/new-releases"  # specify a url
    soup = request_soup(url)  # request the soup
    latest_fiction_id = int(
        soup.find("a", attrs={"class": "font-red-sunglo bold"})
        .get("href")
        .split("/")[2]
    )  # search the html for the latest fiction id
    return latest_fiction_id  # return the latest fiction id


def get_chapter_range(start_chapter: int, end_chapter: int) -> Tuple[int, int, int]:
    assert start_chapter >= 0
    assert end_chapter >= start_chapter

    epub_index_start = start_chapter
    start_chapter -= 1

    return (
        start_chapter,
        end_chapter,
        epub_index_start,
    )


def chapter_range_string_expressions(
    start_chapter,
    end_chapter,
    epub_index_start,
    chapter_amount,
    downloading_chapter_amount,
):
    if (
        downloading_chapter_amount > 1
    ):  # more than one, make prints pretty by recognising plurals
        plural = "s"  # add an s to the end
    else:  # it's only one
        plural = ""  # so no s is needed
    if end_chapter > chapter_amount:  # make sure the chapter range is not too large
        end_chapter = chapter_amount  # set to max
    if start_chapter > chapter_amount:  # make sure the chapter range is not too large
        start_chapter = chapter_amount  # set to max
    if (
        downloading_chapter_amount != chapter_amount
    ):  # if the amount isn't the entire fiction
        if downloading_chapter_amount != 1:  # if the chapter range is more than one
            file_name_chapter_range = (
                " " + str(epub_index_start) + "-" + str(end_chapter)
            )  # name the file with the range
        else:  # if the chapter range is only 1
            file_name_chapter_range = " " + str(
                epub_index_start
            )  # name the file with the chapter
    else:
        file_name_chapter_range = ""  # name the fiction normally without a range
    return (
        start_chapter,
        end_chapter,
        epub_index_start,
        chapter_amount,
        downloading_chapter_amount,
        file_name_chapter_range,
        plural,
    )  # return values to continue download


def search_fiction(search_term):  # search royalroad for a fiction using a given string
    search_term = search_term.replace(" ", "+")  # replace spaces with plus signs
    url = "https://www.royalroad.com/fictions/search?title=" + str(
        search_term
    )  # construct the url
    print(url)  # print the search url for debug or console purposes
    soup = request_soup(url)  # request the soup
    try:
        fiction_id = (
            soup.find(
                "div",
                attrs={"class": "col-sm-10 col-md-8 col-lg-9 col-xs-12 search-content"},
            )
            .find("input")
            .get("id")
            .split("-")[1]
        )  # attempt to gather the first fiction id
    except:  # there was no fiction id or the html is incorrect
        return None  # return none
    return fiction_id  # return the fiction id


def get_fiction_location(
    fiction_id, directory="Fictions/", start_chapter="first", end_chapter="last"
):  # without downloading the fiction, determine where it would be stored exactly
    try:
        int(fiction_id)  # check if fiction_id is a fiction id
    except:  # it isn't
        search_term = fiction_id  # declare search_term
        fiction_id = search_fiction(
            search_term
        )  # perform a search and return the most likely fiction_id
    fiction_object = get_fiction_object(fiction_id)  # collect the fiction page html
    get_fiction_info(
        fiction_object
    )  # collect the data from the fiction page and store it in global variables
    start_chapter, end_chapter, epub_index_start = get_chapter_range(
        start_chapter, end_chapter
    )  # validate and return a chapter range
    chapter_links_approved = chapter_links[
        start_chapter:end_chapter
    ]  # trim off excess chapters outside the range from the queue
    downloading_chapter_amount = len(
        chapter_links_approved
    )  # get the amount of chapters being downloaded
    chapter_amount = len(chapter_links)  # get the total amount of chapters
    if chapter_links_approved != []:  # if there are chapters queued
        (
            start_chapter,
            end_chapter,
            epub_index_start,
            chapter_amount,
            downloading_chapter_amount,
            file_name_chapter_range,
            plural,
        ) = chapter_range_string_expressions(
            start_chapter,
            end_chapter,
            epub_index_start,
            chapter_amount,
            downloading_chapter_amount,
        )  # update all the values
    else:
        file_name_chapter_range = ""  # set the variable as empty
    try:
        final_location = determine_file_location(
            title, directory, author, file_name_chapter_range, fiction_id
        )  # finally collate all the information into a final location
    except:
        final_location = None  # it failed so equate to none
    return final_location  # return the final location


def determine_file_location(
    title, directory, author, file_name_chapter_range, fiction_id
):
    title = re.sub(
        r'[\\/*?:"<>|]', "", re.sub(r"[<>]", "", title)
    ).strip()  # prevent breaking the xhtml because of html characters
    try:
        if author[-1] == "?":  # if the questionmark is the last character
            author = author.replace(
                "?", "qstnmrk"
            )  # prevent an empty name when the ? are removed if they are the last character
    except:
        author = "Unknown"  # the name is probably empty
    author = re.sub(r'[\\/*?:"<>|]', "", author).strip()  # remove invalid characters
    try:
        if author[-1] == ".":  # if the period is the last character
            author = author.replace(
                ".", "dot"
            ).strip()  # replace all periods if they are the last character to prevent extension issues
    except:
        author = "Unknown"  # the name is probably empty
    title = title.strip()
    author = author.strip()
    final_location = (
        directory
        + str(fiction_id)
        + " - "
        + title
        + " - "
        + author
        + file_name_chapter_range
        + ".epub"
    )  # collact all previous information
    return final_location  # return the final location


def get_fiction_object(fiction_id: int) -> BeautifulSoup:
    global url, title, cover_image, author, description, genres, ratings, stats, chapter_links, chapter_amount
    (
        url,
        title,
        cover_image,
        author,
        description,
        genres,
        ratings,
        stats,
        chapter_links,
        chapter_amount,
    ) = [None for i in range(10)]
    url = "https://www.royalroad.com/fiction/" + str(fiction_id)
    soup = request_soup(url)
    assert soup is not None

    active = check_active_fiction(soup, fiction_id)
    assert active

    return soup


def request_soup(url: str) -> Optional[BeautifulSoup]:
    try:
        http_client = httpclient.HTTPClient()
        html = http_client.fetch(url).body.decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        if soup.find(has_cloud_flare_data):
            soup = decode_email_content(soup)
        return soup
    except httpclient.HTTPError as e:
        if e.code != 404:
            return request_soup(url)
        return None


class fic:
    url: str
    title: str
    cover_image: str
    author: str
    description: str
    genres: List[str]
    ratings: float
    stats: Dict[str, str]
    chapter_links: List[str]
    num_chapters: int

    _fic_page_soup: BeautifulSoup

    def __init__(self, fiction_id) -> None:
        self._fic_page_soup = get_fiction_object(fiction_id)
        self._get_fiction_info()

    @staticmethod
    def _get_fiction_cover_image(soup: BeautifulSoup) -> str:
        image_elt = soup.find("meta", attrs={"property": "og:image"})
        assert image_elt is not None
        cover_image = image_elt.get("content")
        cover_image = cast(str, cover_image)

        if (
            cover_image.lower() == "/content/images/nocover-new-min.png"
            or cover_image.lower() == "undefined"
        ):
            cover_image = "http://www.royalroad.com/Content/Images/nocover-new-min.png"
        return cover_image

    @staticmethod
    def _get_fiction_title(soup: BeautifulSoup) -> str:
        title_elt = soup.find("meta", attrs={"name": "twitter:title"})
        assert title_elt is not None, soup

        title = title_elt.get("content")
        title = cast(str, title)

        return title

    @staticmethod
    def _get_fiction_author(soup: BeautifulSoup) -> str:
        author_elt = soup.find("meta", attrs={"property": "books:author"})
        assert author_elt is not None

        author = author_elt.get("content")
        author = cast(str, author)

        return author

    def _get_fiction_info(self):
        assert self._fic_page_soup is not None
        fiction_obj = self._fic_page_soup

        global url, title, cover_image, author, description, genres, ratings, stats, chapter_links, chapter_amount

        fiction_id = get_fiction_id(fiction_obj)
        print(fiction_id)

        self.url = "https://www.royalroad.com/fiction/" + str(fiction_id)
        self.title = self._get_fiction_title(fiction_obj)
        self.cover_image = self._get_fiction_cover_image(fiction_obj)
        self.author = self._get_fiction_author(fiction_obj)
        self.description = get_fiction_description(fiction_obj)
        self.genres = get_fiction_genres(fiction_obj)
        self.ratings = get_fiction_rating(fiction_obj)
        self.stats = get_fiction_statistics(fiction_obj)
        self.chapter_links = get_chapter_links(fiction_obj)
        self.num_chapters = len(self.chapter_links)
        return (
            self.url,
            self.title,
            self.cover_image,
            self.author,
            self.description,
            self.genres,
            self.ratings,
            self.stats,
            self.chapter_links,
            self.num_chapters,
        )


def get_fiction_id(fic_page_soup: BeautifulSoup) -> int:
    # <link href="https://www.royalroad.com/fiction/1234/fic-name" rel="canonical"/>
    input_elt = fic_page_soup.find("link", attrs={"rel": "canonical"})
    assert input_elt is not None

    # https://www.royalroad.com/fiction/1234/fic-name
    link_text = cast(str, input_elt.get("href"))

    prefix = "https://www.royalroad.com/fiction/"
    assert len(link_text) >= len(prefix), link_text

    link_text_suffix = link_text[len(prefix) :]
    slash_ix = link_text_suffix.find("/")

    assert slash_ix >= 0, link_text
    fiction_id = link_text_suffix[:slash_ix]

    try:
        int(fiction_id)
    except:
        assert False, fiction_id

    return int(fiction_id)


def check_active_fiction(soup: BeautifulSoup, fiction_id) -> Optional[bool]:
    not_active = soup.find("div", attrs={"class": "number font-red-sunglo"})
    if not not_active:
        return True
    print(f"No Fiction with ID {fiction_id}")
    return None


def get_fiction_description(soup):
    description = soup.find("div", attrs={"class": "description"}).text.strip()
    if description == "":
        description = "No Description"
    return description


def get_fiction_genres(soup) -> List[str]:
    genres = []
    genre_tags_part1 = soup.findAll(
        "span", attrs={"class": "label label-default label-sm bg-blue-hoki"}
    )
    genre_tags_part2 = soup.findAll("span", attrs={"property": "genre"})
    for tag in genre_tags_part1:
        genres.append(tag.text.strip())
    for tag in genre_tags_part2:
        genres.append(tag.text.strip())
    return genres


def get_fiction_rating(soup) -> float:
    rating_value = soup.find("meta", attrs={"property": "books:rating:value"}).get(
        "content"
    )
    rating_scale = soup.find("meta", attrs={"property": "books:rating:scale"}).get(
        "content"
    )
    assert rating_scale == "5"

    return float(rating_value)


def get_fiction_statistics(soup) -> Dict[str, str]:
    stats = [
        stat.text.strip()
        for stat in soup.findAll(
            "li", attrs={"class": "bold uppercase font-red-sunglo"}
        )
    ][
        :6
    ]  # collate stats like total_views,average_views,followers,favorites,rating_amount,pages
    return stats  # return stats


def get_chapter_links(soup) -> List[str]:
    chapter_links = [
        tag.get("data-url")
        for tag in soup.findAll("tr", attrs={"style": "cursor: pointer"})
    ]
    return chapter_links


def get_chapter_amount(soup):  # get chapter amount
    chapter_amount = len(
        get_chapter_links(soup)
    )  # get chapter links and then find the len of the list
    return chapter_amount  # return chapter amount


async def get_chapters(chapter_links: List[str], directory_loc: str):
    global chapters_downloaded, chapters_html, fiction_html, directory, http_client
    globals()["directory"] = directory_loc
    chapters_downloaded = []
    chapters_html = {}
    fiction_html = ""
    http_client = httpclient.AsyncHTTPClient(force_instance=True, max_clients=100)
    chapter_futures: List[Future[HTTPResponse]] = []
    for chapter_id in chapter_links:
        global i
        i += 1
        url = "https://www.royalroad.com" + str(chapter_id)
        print(url)
        chapter_futures.append(
            http_client.fetch(
                url.strip(),
                True,
                method="GET",
                connect_timeout=10000,
                request_timeout=10000,
            )
        )

    for chap in chapter_futures:
        resp = await chap
        handle_chapter_response(resp)

    save_to_hdd(fiction_html, chapters_html, chapters_downloaded, directory)


def get_chapter_content(html):  # get the chapter html from the chapter page
    soup = BeautifulSoup(html, "lxml")  # create a soup object
    chapter_title = soup.find(
        "h1", attrs={"style": "margin-top: 10px", "class": "font-white"}
    )  # extract the chapter title and strip it
    if chapter_title.find(has_cloud_flare_data):
        chapter_title = decode_email_content(chapter_title)
    chapter_title = chapter_title.text.strip()
    content_html = soup.find(
        "div", attrs={"class": "chapter-inner chapter-content"}
    )  # extract the chapter html and convert it to a str to prevent type errors
    if content_html.find(has_cloud_flare_data):
        content_html = decode_email_content(content_html)
    content_html = str(content_html)
    return content_html, chapter_title  # return the chapter html and chapter title


def save_to_hdd(
    fiction_html, chapters_html, chapters_downloaded, directory="Fictions/"
):
    global url, title, cover_image, author, description, genres, ratings, stats, chapter_links, chapter_amount, epub_index_start, file_name_chapter_range, plural
    time = datetime.now().strftime("%Y-%m-%d %H:%M")
    genre_html = ""
    for genre in genres:
        if genre_html == "":
            genre_html += genre
        else:
            genre_html += " | " + genre
    if file_name_chapter_range != "":
        chapter_range_text = f"{plural} {file_name_chapter_range}"  # specify the chapters contained in the epub
    elif chapter_amount != 1:  # else
        chapter_range_text = (
            f"{plural} 1-{chapter_amount}"  # add it to the start of the epub info
        )
    else:
        chapter_range_text = (
            f"{plural} 1"  # specify that there is only a single chapter in the fiction
        )
    chapter_range_html = f"<h2>Chapter{chapter_range_text}</h2>"
    # maybe use &gt; amd &lt; in the title and author internal
    title_clean = re.sub(
        r'[\\/*"<>]', "", title
    ).strip()  # these are fine for inside the epub
    author_clean = re.sub(
        r'[\\/*"<>]', "", author
    ).strip()  # these are fine for inside the epub
    title_folder = re.sub(
        r"[?:|]", "", title_clean
    ).strip()  # clean the title for windows and other systems
    try:
        if author[-1] == "?":  # check for a question mark as the last character
            author = author.replace(
                "?", "qstnmrk"
            )  # if so, replace it with 'qstnmrk' to prevent empty author names
    except:
        author = "Unknown"  # the name is likely empty and is replaced with 'Unknown'
    author_folder = re.sub(r"[?:|]", "", author_clean).strip()  # clean the author
    try:
        if author_clean[-1] == ".":  # check the clean author for a dot
            author_clean = author_clean.replace(
                ".", "dot"
            )  # if so, replace it as it might cause extension problems, or windows might remove it because of having 2 or more periods in a row
    except:
        author_clean = (
            "Unknown"  # the author_clean is likely empty so replace it with 'Unknown'
        )
    title_internal = title_folder.replace("&", "&amp;").strip()
    author_internal = author_folder.replace("&", "&amp;").strip()
    stats_html = (
        "<p><b>Total Views:</b> "
        + stats[0]
        + "<b> | Average Views:</b> "
        + stats[1]
        + "<b> | Followers:</b> "
        + stats[2]
        + "<b> | Favorites:</b> "
        + stats[3]
        + "<b> | Pages:</b> "
        + stats[5]
        + "</p>"
    )  # format the stats into html
    statistics = (
        "<p><b>Chapters:</b> "
        + str(chapter_amount)
        + "<b> | Overall Score:</b> "
        + ratings[0]
        + "<b> | Best Score:</b> "
        + ratings[1]
        + "<b> | Ratings:</b> "
        + ratings[2]
        + "</p><p><b>Style Score:</b> "
        + ratings[3]
        + "<b> | Story Score:</b> "
        + ratings[4]
        + "<b> | Character Score:</b> "
        + ratings[5]
        + "<b> | Grammar Score:</b> "
        + ratings[6]
        + "</p>"
        + stats_html
    )  # format for info into html
    data = (
        "<div style='text-align: center'><img src='../cover.jpg' alt='Cover Image' style='display: block; margin-left: auto; margin-right: auto;' /><h1>\"<a href='"
        + url
        + "'>"
        + str(title_internal)
        + '</a>" by "'
        + str(author_internal)
        + '"</h1>'
        + chapter_range_html
        + "<p><b>"
        + genre_html
        + "</b></p>"
        + statistics
        + "<h2>Last updated: "
        + time
        + "</h2></div><h3>Description:</h3><p>"
        + str(description)
        + "</p>"
    )  # add the last few pieces of info to the html
    fiction_id = url.split("/")[-1].strip()
    print(
        "Saving EPUB: "
        + directory
        + str(fiction_id)
        + " - "
        + title_folder
        + " - "
        + author_folder
        + file_name_chapter_range
        + ".epub"
    )  # output the final location to the console
    name = (
        fiction_id
        + " - "
        + title_folder
        + " - "
        + author_folder
        + file_name_chapter_range
    )  # create the name variable using the clean title and author with the chapter range
    folder_name = name + "/"  # create the folder name variable
    os.makedirs(
        directory + folder_name + "OEBPS/", exist_ok=True
    )  # make the OEBPS folder for where the epub archive with the chapter html will be located before deletion
    os.makedirs(
        directory + folder_name + "META-INF/", exist_ok=True
    )  # make the META-INF folder for where the epub archive meta-inf will be located before deletion
    os.makedirs(
        directory + folder_name + "OEBPS/style/", exist_ok=True
    )  # make the style folder for where the epub css tables will come from for the formatting before deletion of their root folder, could combine with first os.makedir
    ##    file_name = name + ".html" #create the file name for the html file
    ##    full_path = directory + folder_name + file_name #create the full path for the html file
    ##    with open(full_path, "w", encoding="utf-8") as file_webnovel: #create the html file
    ##        file_webnovel.write(data) #write the fiction data to it
    ##    print("Saved:",full_path) #output the save location to the console
    uuid_str = str(uuid.uuid4())  # create the uuid for the epub

    with open(
        directory + folder_name + "toc.ncx", "w", encoding="utf-8"
    ) as file_toc:  # create and write to the table of contents for the epub with the uuid and title
        file_toc.write(
            """<?xml version='1.0' encoding='UTF-8'?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <head>
    <meta name="dtb:uid" content=\""""
            + uuid_str
            + """\"/>
    <meta name="dtb:generator" content="DumbEpub"/>
    <meta name="dtb:depth" content="2"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>"""
            + str(title_internal)
            + """</text>
  </docTitle>
  <navMap>"""
        )

    with open(
        directory + folder_name + "OEBPS/style/style.css", "w", encoding="utf-8"
    ) as file_css:  # write the css code for the tables found on royalroad
        file_css.write(
            """.chapter-content table,.forum .post-content table {
background:#004b7a;
width:90%;
border:none;
box-shadow:1px 1px 1px rgba(0,0,0,.75);
border-collapse:separate;
border-spacing:2px;
margin:10px auto;
}

.chapter-content table td,.forum .post-content table td {
color:#ccc;
border:1px solid hsla(0,0%,100%,.25)!important;
background:rgba(0,0,0,.1);
margin:3px;
padding:5px;
}"""
        )

    with open(
        directory + folder_name + "META-INF/container.xml", "w", encoding="utf-8"
    ) as file_container:  # create and write to the file container for the epub with info about the content.opf
        file_container.write(
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
	<rootfiles>
		<rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
	</rootfiles>
</container>"""
        )

    with open(
        directory + folder_name + "content.opf", "w", encoding="utf-8"
    ) as file_content:  # create and write to the content file for the epub with info about the uuid, author and title
        file_content.write(
            """<?xml version='1.0' encoding='UTF-8'?>
<opf:package version="2.0" unique-identifier="BookId" xmlns:opf="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <opf:metadata>
    <dc:identifier id="BookId" opf:scheme="UUID">"""
            + uuid_str
            + """</dc:identifier>
    <dc:title>"""
            + title_internal
            + """</dc:title>
    <dc:creator opf:role="aut">"""
            + author_internal
            + """</dc:creator>
    <dc:language>en</dc:language>
    <dc:language>eng</dc:language>
    <opf:meta name="generator" content="DumbEpub"/>
    <opf:meta name="cover" content="cover"/>
  </opf:metadata>
  <opf:manifest>
    <opf:item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <opf:item id="cover" href="cover.jpg" media-type="image/jpeg"/>
    <opf:item id="css-style" href="OEBPS/style/style.css" media-type="text/css"/>
    <opf:item id="cover-page" href="titlepage.xhtml" media-type="application/xhtml+xml"/>
    <opf:item id="prov_idx_1" href="OEBPS/info.xhtml" media-type="application/xhtml+xml"/>"""
        )

    for i in range(
        epub_index_start, epub_index_start + len(chapters_downloaded)
    ):  # for each chapter number
        with open(
            directory + folder_name + "content.opf", "a", encoding="utf-8"
        ) as file_content:  # append a line container the link to the file internally and its index num
            file_content.write(
                """
    <opf:item id="prov_idx_"""
                + str(i + 1)
                + """\" href="OEBPS/chapter_"""
                + str(i)
                + """.xhtml" media-type="application/xhtml+xml"/>"""
            )

    with open(
        directory + folder_name + "content.opf", "a", encoding="utf-8"
    ) as file_content:  # append the end tags to the content file
        file_content.write(
            """
  </opf:manifest>
  <opf:spine toc="ncx">"""
        )

    with open(
        directory + folder_name + "toc.ncx", "a", encoding="utf-8"
    ) as file_toc:  # append the info page to the table of contents
        file_toc.write(
            """
    <navPoint class="chapter" id="navPoint-"""
            + str(0)
            + """\" playOrder=\""""
            + str(1)
            + """\">
      <navLabel>
        <text>Information</text>
      </navLabel>
      <content src="OEBPS/info.xhtml"/>
    </navPoint>"""
        )

    full_path = (
        directory + folder_name + "OEBPS/info.xhtml"
    )  # declare the full path to the info page html

    with open(
        full_path, "w", encoding="utf-8"
    ) as file_info:  # write to the info page xhtml file with all the info data html
        file_info.write(
            """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
				<head>
					<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
					<title>Information</title>
				</head>
				<body>
					"""
            + data
            + """</body>
			</html>"""
        )

    with open(
        directory + folder_name + "content.opf", "a", encoding="utf-8"
    ) as file_content:  # append the itemref opening tag to the content file
        file_content.write(
            """
    <opf:itemref idref="prov_idx_1\"/>"""
        )

    chp = epub_index_start - 1  # declare the starting chapter number
    for chp_id in chapters_downloaded:  # for each chapter id that was downloaded
        chp += 1  # add one to the chp number
        chapter_title_clean = (
            chapters_html[chp_id][1]
            .replace("<", "")
            .replace(">", "")
            .replace("&", "&amp;")
        )  # TODO check if amp should be used here, it should be probably but is applied lower too
        chapter_title = f"({chp}) {chapter_title_clean}"  # and use it to name the chapter title with the original chapter title
        chapter_html = (
            '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<html xmlns="http://www.w3.org/1999/xhtml">\n\t\t\t\t<head>\n\t\t\t\t\t<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n\t\t\t\t\t<title>Chapter '
            + str(chp)
            + ": "
            + chapter_title_clean
            + '</title>\n\t\t\t\t\t<link href="style/style.css" rel="stylesheet" type="text/css"/>\n\t\t\t\t</head>\n\t\t\t\t<body>\n\t\t\t\t\t<h1>'
            + chapters_html[chp_id][1]
            + "</h1>\n\t\t\t\t\t"
            + chapters_html[chp_id][0]
            + "\n\t\t\t\t</body>\n\t\t\t</html>"
        )  # create the internal epub chapter html
        chapter_file_name = (
            "chapter_" + str(chp) + ".xhtml"
        )  # name the chapter file appropriately
        full_path = (
            directory + folder_name + "OEBPS/" + chapter_file_name
        )  # declare the full path

        with open(
            full_path, "w", encoding="utf-8"
        ) as file_chapter:  # create and open the chapter xhtml and write the the html to it
            file_chapter.write(chapter_html.replace("&", "&#38;"))

        with open(
            directory + folder_name + "toc.ncx", "a", encoding="utf-8"
        ) as file_toc:  # append the chapter reference to the table of content, while cleaning up the title
            file_toc.write(
                """
    <navPoint class="chapter" id="navPoint-"""
                + str(chp)
                + """\" playOrder=\""""
                + str(chp + 1)
                + """\">
      <navLabel>
        <text>"""
                + chapter_title.replace("&", "&#38;")
                + """</text>
      </navLabel>
      <content src="OEBPS/chapter_"""
                + str(chp)
                + """.xhtml"/>
    </navPoint>"""
            )

        with open(
            directory + folder_name + "content.opf", "a", encoding="utf-8"
        ) as file_content:  # append the internal chapter reference to the content.opf file
            file_content.write(
                """
    <opf:itemref idref="prov_idx_"""
                + str(chp + 1)
                + """\"/>"""
            )

    with open(
        directory + folder_name + "content.opf", "a", encoding="utf-8"
    ) as file_content:  # append the cover titlepage to the content.opf file
        file_content.write(
            """
  </opf:spine>
  <opf:guide>
    <opf:reference href="titlepage.xhtml" title="Cover" type="cover"/>
  </opf:guide>
</opf:package>"""
        )

    with open(
        directory + folder_name + "toc.ncx", "a", encoding="utf-8"
    ) as file_toc:  # append the closing tags to the table of contents file
        file_toc.write(
            """
  </navMap>
</ncx>"""
        )
    with open(
        directory + folder_name + "titlepage.xhtml", "w", encoding="utf-8"
    ) as titlepage:  # create and open the title page and write the cover image internal address to it, for pretty display in epub reading software
        titlepage.write(
            """<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <meta name="calibre:cover" content="true" />
        <title>Cover</title>
        <style type="text/css" title="override_css">
            @page {padding: 0pt; margin:0pt}
            body { text-align: center; padding:0pt; margin: 0pt; }
        </style>
    </head>
    <body>
        <div>
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                width="100%" height="100%" viewBox="0 0 600 800"
                preserveAspectRatio="none">
                <image width="600" height="800" xlink:href="cover.jpg"/>
            </svg>
        </div>
    </body>
</html>"""
        )
    output_location = directory  # declare the output location
    folder_location = directory + folder_name  # declare the folder location
    obtain_and_save_image(
        folder_location, cover_image
    )  # either decode the base64 image or download the image from the external image address and save it
    compress_and_convert_to_epub(
        directory, folder_location, output_location
    )  # compress and covert the epub from the local archive that was created and then remove the archive and folder


def obtain_and_save_image(
    directory, cover_image
):  # decode the base64 image or download the image and then save it
    if (
        (cover_image.split(",")[0] != "data:image/jpeg;base64")
        and (cover_image.split(",")[0] != "data:image/gif;base64")
        and (cover_image.split(",")[0] != "data:image/png;base64")
    ):  # if the image is not base64 encoded
        if (
            cover_image == "http://www.royalroad.com/Content/Images/nocover-new-min.png"
        ):  # don't download the default image to save data
            try:
                with open("nocover.jpg", "rb") as nocover:
                    image_data = nocover.read()
            except:
                image_data = download_image_data(
                    "http://www.royalroad.com/Content/Images/rr-placeholder.jpg"
                )
        else:
            image_data = download_image_data(cover_image)  # download the image
        if image_data == None:  # if the image is empty
            image_data = download_image_data(
                "http://www.royalroad.com/Content/Images/rr-placeholder.jpg"
            )  # download the default image instead
    else:  # else decode the image if it is base64 encoded
        try:
            image_data = base64.b64decode(image_data)  # decode the image
        except:
            image_data = download_image_data(
                "http://www.royalroad.com/Content/Images/rr-placeholder.jpg"
            )  # download the default image if the decode fails
    try:
        with open(
            directory + "cover.jpg", "wb"
        ) as cover_image_file:  # write the image data to the local location in bytes
            cover_image_file.write(image_data)
    except:
        image_data = download_image_data(
            "http://www.royalroad.com/Content/Images/rr-placeholder.jpg"
        )  # download the default image if the decode fails
        with open(
            directory + "cover.jpg", "wb"
        ) as cover_image_file:  # write the image data to the local location in bytes
            cover_image_file.write(image_data)


def download_image_data(cover_image):  # download the image data
    try:
        http_client_image = httpclient.HTTPClient()  # initiate the http request
        image_data = http_client_image.fetch(
            cover_image, headers=headers
        ).body  # collect the body from the response
        return image_data  # return the image data
    except httpclient.HTTPError:  # if a http error occurs
        try:
            if e.code != 404:  # and it's not a 404, retry the download
                download_image_data(cover_image)
        except:
            download_image_data(
                "http://www.royalroad.com/Content/Images/rr-placeholder.jpg"
            )  # else download the default image


def compress_and_convert_to_epub(
    directory, folder_location, output_location
):  # compress and convert the file to epub
    global final_location  # access global variables
    new_zip_name = folder_location.split("/")[
        -2
    ]  # create a zip name based on the current folder name
    output_location = (
        directory + new_zip_name
    )  # declare the output location of the archive function
    zip_file_epub = zipfile.ZipFile(output_location + ".zip", "w")  # create a zipfile
    zip_file_epub.writestr(
        "mimetype", "application/epub+zip"
    )  # write a mimetype file as the FIRST FILE in the zip, this is critical to the function of an epub as it is the only method of identifying it (must be the first file)
    addFolderToZip(
        zip_file_epub, folder_location
    )  # add the prepared epub contents to the zip file
    zip_file_epub.close()  # close the zipfile
    remove_dir(folder_location)  # delete the directory used to make the zipfile
    try:  # to prevent file exists error, fails if file is open
        os.remove(
            output_location + ".epub"
        )  # remove any epubs that already exist with the name of the current epub
    except:
        pass
    try:
        os.rename(
            output_location + ".zip", output_location + ".epub"
        )  # rename the epub zip to be an epub file
    except Exception as e:  # the rename failed (the last step)
        print(
            output_location, "Error", e
        )  # the file likely already exists and as such the old one must be manually remove and then the zip file needs to be renamed manually
    final_location = (
        output_location + ".epub"
    )  # declare the final location of the epub file
    print(
        "Saved EPUB:", final_location
    )  # print the saved location of the epub to the console


def remove_dir(folder_location):  # remove a dir
    try:
        rmtree(folder_location)  # remove all nested directories
    except:
        os.listdir(folder_location)  # if that fails list the directory, maybe useless?
        remove_dir(folder_location)  # remove the directory


def addFolderToZip(
    zip_file_epub, folder_location
):  # add a folder recursively to a zip file
    for file in os.listdir(folder_location):  # for each file in a directory
        full_path = os.path.join(
            folder_location, file
        )  # construct the full path to the file
        if os.path.isfile(full_path):  # if the path is correct
            zip_file_epub.write(
                str(full_path),
                str("/".join(full_path.split("/")[2:])),
                zipfile.ZIP_DEFLATED,
            )  # add the file to the zip
        elif os.path.isdir(full_path):  # if the path is actually a folder
            addFolderToZip(zip_file_epub, full_path)  # add that folder to the zip too


def decode_email_content(soup):
    emails = soup.find_all(has_cloud_flare_data)
    for email_protected in emails:
        data = email_protected.get("data-cfemail")
        email = decode_email(data)
        email_protected.replaceWith(email)
    return soup


def decode_email(data_string):
    email = ""
    r = int(data_string[:2], 16)
    i = 2
    while len(data_string) - i:
        char = int(data_string[i : i + 2], 16) ^ r
        email += chr(char)
        i += 2
    return email


def has_cloud_flare_data(tag):
    return tag.has_attr("data-cfemail")


def cloud_flare_bypass():
    global headers
    WINDOW_SIZE = "1920,1080"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36"
    chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    chrome_options.add_argument("user-agent=" + user_agent)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.royalroad.com/")
    driver.get_screenshot_as_file("capture.png")
    time.sleep(10)
    # html = driver.page_source
    cookies = " ".join(
        [c["name"] + "=" + c["value"] + ";" for c in driver.get_cookies()]
    )
    headers = {"user-agent": user_agent, "cookie": cookies}
    driver.close()
    return headers


def handle_chapter_response(response):
    global i, chapters_downloaded, chapters_html, fiction_html, directory, http_client  # access global variables
    if response.code == 599:  # if the request failed (timeout or 404)
        print(response.effective_url, "error")  # print an error to the console
        http_client.fetch(
            response.effective_url.strip(),
            handle_chapter_response,
            method="GET",
            connect_timeout=10,
            request_timeout=10,
            headers=headers,
        )  # add the failed url to the loop and give it a 10 second timeout
    else:
        html = response.body.decode("utf-8")  # decode the response html
        url = response.effective_url  # clarify the url of the response
        if (
            "Could not find host | www.royalroad.com | Cloudflare".lower()
            in html.lower()
        ):  # if the page is incorrect and actually a cloudflare auto flag
            print(
                "Cloudflare Problem! Retrying"
            )  # alert the console that cloudflare is interfering
            http_client.fetch(
                response.effective_url.strip(),
                handle_chapter_response,
                method="GET",
                connect_timeout=10,
                request_timeout=10,
                headers=headers,
            )  # retry the chapter request with a 10 second timeout
        else:  # if the page is not cloudflare
            try:
                chapter_id = int(url.split("/")[-2])  # get the chapter id from the url
            except:
                chapter_id = int(
                    url.split("?")[0].split("/")[-1]
                )  # the chapter id is presented weirdly occasionally and as such this is the other method to get the chapter id from the url
            try:
                chapters_downloaded.append(
                    chapter_id
                )  # append the chapter id to the chapters_downloaded list
                html = get_chapter_content(
                    html
                )  # get the html content of the chapter from the page
                chapters_html[
                    chapter_id
                ] = html  # set the chapter id value in the chapters_html dictionary to the chapter html
                i -= 1  # subtract 1 from the remaining chapter links
                if i == 0:  # if all the chapters are downloaded for the fiction
                    chapters_downloaded.sort(
                        key=int
                    )  # sort the chapter ids so the fiction is in chronological order (very important)
                    chp = 0  # declare chp as 0
                    for chp_id in chapters_downloaded:  # for each chp id downloaded
                        chp += 1  # add one to chp count
                        # fiction_html = fiction_html + "<div style='text-align: center'><h1 style='margin-top: 10px' class='font-white'>(" + str(chp) + ") " + chapters_html[chp_id][1] + "</div></h1>" + chapters_html[chp_id][0] #and append the entire chapter html to the rest of the story
                    ioloop.IOLoop.instance().stop()  # stop the ioloop and then progress to the save_to_hdd function

            except:  # something went wrong, probably empty response, retry
                cloud_flare_bypass()
                http_client.fetch(
                    response.effective_url.strip(),
                    handle_chapter_response,
                    method="GET",
                    connect_timeout=10,
                    request_timeout=10,
                    headers=headers,
                )
