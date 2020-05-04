# encoding=utf-8

from flask import Flask, render_template,request


import jieba
import jieba.posseg as pseg
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import OrderedDict
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


import question_temp



class JenaFuseki:
    def __init__(self, endpoint_url='http://localhost:3030/kg_demo_movie/query'):
        self.sparql_conn = SPARQLWrapper(endpoint_url)

    def get_sparql_result(self, query):
        self.sparql_conn.setQuery(query)
        self.sparql_conn.setReturnFormat(JSON)
        return self.sparql_conn.query().convert()

    @staticmethod
    def parse_result(query_result):
        """
        解析返回的结果
        :param query_result:
        :return:
        """
        try:
            query_head = query_result['head']['vars']
            query_results = list()
            for r in query_result['results']['bindings']:
                temp_dict = OrderedDict()
                for h in query_head:
                    temp_dict[h] = r[h]['value']
                query_results.append(temp_dict)
            return query_head, query_results
        except KeyError:
            return None, query_result['boolean']

    def print_result_to_string(self, query_result):
        """
        直接打印结果，用于测试
        :param query_result:
        :return:
        """
        query_head, query_result = self.parse_result(query_result)

        if query_head is None:
            if query_result is True:
                print ('Yes')
            else:
                print ('False')
            print
        else:
            for h in query_head:
                print (h, ' '*5)
            print
            for qr in query_result:
                for _, value in qr.items():
                    print (value, ' ')
                print

    def get_sparql_result_value(self, query_result):
        """
        用列表存储结果的值
        :param query_result:
        :return:
        """
        query_head, query_result = self.parse_result(query_result)
        if query_head is None:
            return query_result
        else:
            values = list()
            for qr in query_result:
                for _, value in qr.items():
                    values.append(value)
            return values


class Word(object):
    def __init__(self, token, pos):
        self.token = token
        self.pos = pos


class Tagger:
    def __init__(self, dict_paths):
        # TODO 加载外部词典
        for p in dict_paths:
            jieba.load_userdict(p)

        # TODO jieba不能正确切分的词语，我们人工调整其频率。
        jieba.suggest_freq(('喜剧', '电影'), True)
        jieba.suggest_freq(('恐怖', '电影'), True)
        jieba.suggest_freq(('科幻', '电影'), True)
        jieba.suggest_freq(('喜剧', '演员'), True)
        jieba.suggest_freq(('出生', '日期'), True)
        jieba.suggest_freq(('英文', '名字'), True)

    @staticmethod
    def get_word_objects(sentence):
        # type: (str) -> list
        """
        把自然语言转为Word对象
        :param sentence:
        :return:
        """
        return [Word(word, tag) for word, tag in pseg.cut(sentence)]


class Question2Sparql:
    def __init__(self, dict_paths):
        self.tw = Tagger(dict_paths)
        self.rules = question_temp.rules

    def get_sparql(self, question):
        """
        进行语义解析，找到匹配的模板，返回对应的SPARQL查询语句
        :param question:
        :return:
        """
        word_objects = self.tw.get_word_objects(question)
        queries_dict = dict()

        for rule in self.rules:
            query, num = rule.apply(word_objects)

            if query is not None:
                queries_dict[num] = query

        if len(queries_dict) == 0:
            return None
        elif len(queries_dict) == 1:
            # print(list(queries_dict.values()))
            return list(queries_dict.values())[0]
        else:
            # TODO 匹配多个语句，以匹配关键词最多的句子作为返回结果
            sorted_dict = sorted(queries_dict.items(), key=lambda item: item[0], reverse=True)
            return sorted_dict[0][1]





app = Flask(__name__)


@app.route('/')
def index():

    return  render_template("index.html",val='hello')

@app.route('/',methods=['POST'])
def anser():
    question = request.form.get("question")

    f = open("Q_A.txt", "w+", encoding="utf-8")
    f.write("question: \n")
    f.write(question+"\n")

    question=str(question)
    # print(question)
    my_query = q2s.get_sparql(question)


    f.write("search:\n")
    f.write(my_query)
    # print(my_query)
    if my_query is not None:
        result = fuseki.get_sparql_result(my_query)
        value = fuseki.get_sparql_result_value(result)
        # TODO  ，是布尔值则提问类型是"ASK"，回答“是”或者“不知道”。
        if isinstance(value, bool):
            if value is True:
                f.write("anser:\n")
                f.write("Yes")
                return render_template("index.html", val='Yes',qt=question)
            else:
                f.write("anser:\n")
                f.write("I don\'t know. ")
                return render_template("index.html", val='I don\'t know. :(',qt=question)
        else:

            # TODO 查询结果为空，根据OWA，回答“不知道”
            if len(value) == 0:
                f.write("anser:\n")
                f.write("I don\'t know. ")
                return render_template("index.html", val='I don\'t know.',qt=question)
            elif len(value) == 1:
                f.write("anser:\n")
                f.write(value[0])
                return render_template("index.html", val=value[0],qt=question)
            else:

                output = ''
                for v in value:
                    output += v + u' ; '
                f.write("anser:\n")
                f.write(output[0:-1])
                return render_template("index.html", val=output[0:-1],qt=question)

    else:
        # TODO 自然语言问题无法匹配到已有的正则模板上，回答“无法理解”
        f.write("anser:\n")
        f.write("I can\'t understand.")
        return render_template("index.html", val='I can\'t understand.',qt=question)


    # print('#' * 100)
    f.write("\n\n\n")


if __name__ == '__main__':
    # TODO 连接Fuseki服务器。
    fuseki = JenaFuseki()
    # TODO 初始化自然语言到SPARQL查询的模块，参数是外部词典列表。
    q2s = Question2Sparql(['./external_dict/movie_title.txt', './external_dict/person_name.txt'])

    app.run(debug=True)

