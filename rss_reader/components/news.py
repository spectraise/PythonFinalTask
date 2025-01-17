"""This module contains a class that represents a feed item"""

from datetime import datetime

from bs4 import BeautifulSoup
from dateutil.parser import parse
import requests


class News:
    """This class represents a feed item"""

    def __init__(self, feed_title, item, source_url, logger, cache, to_colorized_format):
        """
        This class constructor initializes the required variables for the news class

        Parameters:
            feed_title (str): News feed title
            item (bs4.element.Tag): Object of class bs4.element.Tag containing news item
            source_url (str): Link to RSS Feed
            logger (module): logging module
            cache (Cache): Object of class Cache
            to_colorized_format (bool): If True colors the result
        """
        self.feed_title = feed_title
        self.item = item
        self.source_url = source_url
        self.logger = logger
        self.cache = cache
        self.to_colorized_format = to_colorized_format
        if isinstance(self.item, dict):
            self.__from_cache()
        else:
            self.links = {}
            self.title = self.item.title.text
            self.link = self.item.link.text
            self.description = self.__parse_description()
            self.date = self.__parse_date()
            self.formatted_date = datetime.strftime(self.date, '%a, %d %b %G %X')
            self.__parse_enclosure()
            self.__parse_media_content()
            self.cache.cache_news(self)

    def __parse_description(self) -> str:
        """This method parses the description of the feed item and formats it"""
        if self.item.description:
            document_data = BeautifulSoup(self.item.description.text, 'html.parser')
            images = document_data.find_all('img')
            for image in images:
                item_position = len(self.links)
                response = requests.head(image['url'])
                image_type = response.headers['content-type']
                self.links[item_position] = {'enclosure': False, 'media': False, 'type': image_type,
                                             'url': image['src'], 'attributes': {'alt': image['alt']}}
                image.replace_with(f'[image {item_position}{": " + image["alt"] + "] " if image["alt"] else "] "}')
            return document_data.text

    def __parse_date(self) -> datetime:
        """This method parses the publication date of the feed item"""
        if self.item.pubDate:
            date = self.item.pubDate.text
        elif self.item.published:
            date = self.item.published.text
        return parse(date)

    def __format_links(self) -> str:
        """This method returns the formatted links contained in the feed item"""
        return '\n' + '\n'.join(f'[{position}] {link["url"]} ({link["type"]})' for position, link in self.links.items())

    def to_dict(self) -> dict:
        """This method returns a dictionary representation of the news object"""
        return {'title': self.title,
                'url': self.link,
                'description': self.description,
                'date': self.formatted_date,
                'links': self.links if self.links else None}

    def __str__(self) -> str:
        """This method override default __str__ method which computes the string representation of an object"""
        if self.to_colorized_format:
            return f'[{self.colorize_string(self.feed_title, "red")}] {self.colorize_string(self.title, "yellow")}\n' \
                   f'{self.colorize_string("Date:", "cyan")} {self.colorize_string(self.formatted_date, "yellow")}\n' \
                   f'{self.colorize_string("Link:", "cyan")} {self.link}\n\n' \
                   f'{self.colorize_string(self.description, "yellow") if self.description else ""}\n\n' \
                   f'{self.colorize_string("Links:", "cyan") + self.__format_links() if self.links else ""}'.rstrip()
        else:
            return f'[{self.feed_title}] {self.title}\n' \
                   f'Date: {self.formatted_date}\n' \
                   f'Link: {self.link}\n\n' \
                   f'{self.description if self.description else ""}\n\n' \
                   f'{"Links:" + self.__format_links() if self.links else ""}'.rstrip()

    def __from_cache(self):
        """This method retrieves news variables from cached news"""
        self.links = self.item['links']
        self.title = self.item['title']
        self.link = self.item['url']
        self.description = self.item['description']
        self.formatted_date = self.item['date']

    def __parse_enclosure(self):
        """This method parses enclosures from the feed item and adds them to links"""
        enclosure_list = self.item.find_all('enclosure')
        for enclosure in enclosure_list:
            enclosure_type = self.__get_content_type(enclosure)
            self.links[len(self.links)] = {'enclosure': True, 'media': False, 'type': enclosure_type,
                                           'url': enclosure['url'], 'attributes': None}

    def __parse_media_content(self):
        """This method parses media:content from the feed item and adds them to links"""
        media_content_list = self.item.findAll('media:content')
        for media_content in media_content_list:
            media_content_type = self.__get_content_type(media_content)
            self.links[len(self.links)] = {'enclosure': False, 'media': True, 'type': media_content_type,
                                           'url': media_content['url'], 'attributes': None}

    @staticmethod
    def __get_content_type(content):
        """
        This method will determine the content type

        Parameters:
            content (bs4.element.Tag): Object of class bs4.element.Tag with content

        Returns:
            str: Content type
        """
        response = requests.head(content['url'])
        content_type = response.headers.get('content-type')
        if content_type is None:
            content_type = content.get('type')
            if content_type is None:
                content_type = 'unknown'
        return content_type

    @staticmethod
    def colorize_string(string, color):
        """
        This method wraps the string with ANSI escape codes to change the color of the text

        Parameters:
            string (str): String to be escaped
            color (str): Color name

        Returns:
            str: ANSI escaped string
        """
        colors = {'cyan': '\033[1;36m', 'yellow': '\033[1;33m', 'red': '\033[1;31m', 'reset': '\033[0m'}
        return colors[color] + string + colors['reset']
