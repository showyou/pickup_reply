#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys

import re
import simplejson
import model
from collections import defaultdict
import sqlalchemy
from sqlalchemy.orm.exc import NoResultFound
import mecab
import codecs
import random

session = None
def get_auth_data(fileName):
    file = open(fileName,'r')
    a = simplejson.loads(file.read())
    file.close()
    return a


def pickup_reply_tweet(reply_word, word):
    global session
    # reply_wordを含む文章を返す
    print u"入力単語:返信単語",
    print word,reply_word
    q = session.query(model.Reply.reply_text).filter( \
        model.Reply.src_text.like('%'+word.encode("utf-8")+'%'))
    sentences =\
    q.filter(model.Reply.reply_text.like('%'+reply_word.encode("utf-8")+'%'))[0]
    print "send",
    s =re.sub("(@(\w)+\W)", "", sentences[0])
    print s
    return s
    #raise


def pickup_top_used_word(word_total, number):
    # word_total: [単語名:数]
    # number: 取り出す数。1なら1個。nならn個
    sort_item= sorted(word_total.items(), key=lambda x:x[1],reverse=True)[0:number]
    if number > 1:
        l = []
        for si in sort_item:
            l.append(si[0])
        result = random.choice(l)
    else: result = sort_item[0][0]
    #print "result",result
    return result
    raise


def stopwords(s):
    words = [u"ん", u"、", u"ー", u"!!", u"それ", u"(", u"の", u")",
            u"こと", u"そう", u"w", u"RT", u"さ", u"♪", u"さん",u"/",u"ぃ",
            u"〜", u"uR", u"ly", u"//", u"://"]
    for w in words:
        if s == w: return True

    return False


def sparse_sentence(s):
    #print s
    s_sparse =\
    mecab.sparse_all(s.encode("utf-8"),"/usr/lib/libmecab.so.1").split("\n")[:-2]
    candidate = set()
    for s2 in s_sparse: # この時点で単語レベルのハズ(ただしs2=単語 品詞
                        # とかかなぁ
        #print "s2",
        s3 = s2.decode("utf-8").split("\t")
        s4 = s3[1].split(",")

        if s4[0] == u"名詞":
        #if s4[0] != u"記号" and s4[0] != u"助動詞" \
        #    and s4[0] != u"助詞":#数が集まったら名詞のみにしたい
        #    print s3[0],s4[0],s4[1]
            if not stopwords(s3[0]):
                candidate.add(s3[0])
    return candidate


def calc_word_count(sentences):
    global session

    word_total = defaultdict(float)
    for s in sentences:
        word_onesentence_set = sparse_sentence(s)

        for w in word_onesentence_set:
            word_total[w] += 1.0
    
    for k,w in sorted(word_total.items(), key=lambda x:x[1], reverse=True)[:10]:
        print "%s:%d," % (k, w),
    print ""
    
    cnt = 0.0
    for i in word_total.values():
        cnt += i
    
    for k in word_total.keys():
        word_total[k] /= cnt
        

    return word_total
    raise


def select_contain_sentences(word):
    #sqlalchemyに与える文字列は(utf-8)
    global session
    print word,
    q = session.query(model.Reply)
    sentences = q.filter( 
        model.Reply.src_text.like('%'+word.encode("utf-8")+'%'))[0:150]

    print len(sentences)
    result_all = []
    for s in sentences:
        result = re.sub("(@(\w)+\W)", "", s.reply_text)
        result_all.append(result)
    return result_all
    #raise


def pickup_reply_one_word(word):
    sentences = select_contain_sentences( word )
    word_total = calc_word_count(sentences)
    return word_total


"""
    "あつい"と入れると
    1.あつい を含むtweetを列挙
    2.tweetを単語レベルに分解
    3.あつい 以外の単語の出現数を数え上げる(ただし1文につき一回)
"""
def pickup_reply(input_sentence):
    
    word_total = defaultdict(int)
    word_head  = {} #topになったreplyが出る転置インデックス
    words = sparse_sentence(input_sentence)

    if len(words) == 1: words.add("eof")
    #print words
    wordcount = {}
    for word in words:
        #print "w1", word
        if word == "eof": continue
    
        tmp_total = pickup_reply_one_word(word)
        wordcount[word] = tmp_total
        for k,v in tmp_total.iteritems():
            word_total[k]+=v
            if word_head.has_key(k) == False:
                word_head[k] = set([word])
            else:
                word_head[k].add(word)
    
            """
            q = session.query(model.Collocation).filter(
                (model.Collocation.dist == word) &
                (model.Collocation.src  == k))
            try:
                colloc = q.one()
                colloc.count += v
            except sqlalchemy.orm.exc.NoResultFound:
                colloc = model.Collocation()
                colloc.dist = word
                colloc.src = k
                colloc.count = v
            
            session.add(colloc)
            """
    """
    session.commit()
    """

    word_max = {}
    for k,v in word_total.iteritems():
        wc = wordcount.iteritems()
        word_max[k] = max([wv[k]*wv[k]/word_total[k] for wk,wv in wc])
    
    print "total:"
    for k,v in sorted(word_max.items(), key=lambda x:x[1], reverse=True)[:10]:
        print "%s:%.4f" %(k,v),
    print ""


    reply_word = pickup_top_used_word(word_max,5) # 1はTop1だけ取ってくる。
                                       # 2以上ならTop2個とってあとはランダム
    a = word_head[reply_word]
    #print a
    if len(a) > 1:
        src_word = random.choice(list(a))
    else:
        src_word = list(a)[0]
    #print "a",src_word
    print "\n入力文章",input_sentence
    reply_text = pickup_reply_tweet(reply_word, src_word)
    return reply_text


def main():
    global session
    #sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
    user = get_auth_data("config.json")
    session = model.startSession(user)

    #api = auth_api.connect(user["consumer_token"], user["consumer_secret"])
    #api = tweepy_connect.connect()
    if len(sys.argv) > 1:
        in_word = sys.argv[1].decode("utf-8")
    else:
        in_word = u"帰宅"
    pickup_reply(in_word)

if __name__ == "__main__":
    main()
